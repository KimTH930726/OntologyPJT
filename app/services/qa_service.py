from __future__ import annotations

import logging
from dataclasses import dataclass
from time import monotonic
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models.ai_query_log import AIQueryLog
from app.integrations.llm.base import LLMProvider
from app.integrations.llm.factory import get_llm_provider
from app.repositories.ai_query_log_repository import AIQueryLogRepository
from app.services.context_builder import ContextBuilder
from app.services.graph_retriever import GraphRetriever
from app.services.prompt_builder import PromptBuilder
from app.services.vector_retriever import VectorRetriever

logger = logging.getLogger(__name__)


class LLMCallError(Exception):
    """Raised when the LLM provider's ``answer`` call fails. QAService still
    persists the ai_query_log row (with ``error_message``) before re-raising."""

    def __init__(self, message: str, query_log_id: UUID) -> None:
        super().__init__(message)
        self.query_log_id = query_log_id


@dataclass
class QAOutcome:
    answer: str
    seed_entities: list[str]
    triple_count: int
    chunk_count: int
    query_log_id: UUID


class QAService:
    def __init__(
        self,
        db: Session,
        *,
        graph_retriever: GraphRetriever | None = None,
        vector_retriever: VectorRetriever | None = None,
        context_builder: ContextBuilder | None = None,
        prompt_builder: PromptBuilder | None = None,
        provider: LLMProvider | None = None,
        query_log_repo: AIQueryLogRepository | None = None,
        top_k_chunks: int = 5,
        graph_depth: int = 2,
    ) -> None:
        self.db = db
        self.graph_retriever = graph_retriever or GraphRetriever(db)
        self.vector_retriever = vector_retriever or VectorRetriever(db)
        self.context_builder = context_builder or ContextBuilder()
        self.prompt_builder = prompt_builder or PromptBuilder(db)
        self.provider = provider or get_llm_provider()
        self.query_log_repo = query_log_repo or AIQueryLogRepository(db)
        self.top_k_chunks = top_k_chunks
        self.graph_depth = graph_depth

    def answer(self, question: str) -> QAOutcome:
        started = monotonic()

        # 1) Retrieval
        try:
            graph = self.graph_retriever.retrieve(question, depth=self.graph_depth)
        except Exception as e:
            logger.exception("graph retrieval crashed: %s", e)
            from app.services.graph_retriever import GraphRetrievalResult

            graph = GraphRetrievalResult()

        try:
            vector = self.vector_retriever.retrieve(
                question, graph.evidence_chunk_ids, top_k=self.top_k_chunks
            )
        except Exception as e:
            logger.exception("vector retrieval crashed: %s", e)
            from app.services.vector_retriever import VectorRetrievalResult

            vector = VectorRetrievalResult()

        # 2) Context + Prompt
        context = self.context_builder.build(graph, vector)
        final_prompt = self.prompt_builder.build_qa(context, question)

        # 3) Fallback: no graph, no evidence → skip LLM, return canned message.
        if not graph.triples and not vector.chunks:
            answer_text = (
                "근거 부족: 제공된 Graph Context와 Document Evidence만으로는 판단할 수 없습니다."
            )
            log_row = self._persist_log(
                question=question,
                graph=graph,
                vector=vector,
                final_prompt=final_prompt,
                answer=answer_text,
                latency_ms=int((monotonic() - started) * 1000),
                error_message=None,
            )
            return QAOutcome(
                answer=answer_text,
                seed_entities=graph.seed_entities,
                triple_count=len(graph.triples),
                chunk_count=len(vector.chunks),
                query_log_id=log_row.id,
            )

        # 4) LLM call
        try:
            answer_text = self.provider.answer(final_prompt)
        except Exception as e:
            logger.exception("LLM provider answer failed: %s", e)
            log_row = self._persist_log(
                question=question,
                graph=graph,
                vector=vector,
                final_prompt=final_prompt,
                answer=None,
                latency_ms=int((monotonic() - started) * 1000),
                error_message=f"{type(e).__name__}: {e}",
            )
            raise LLMCallError(str(e), query_log_id=log_row.id) from e

        # 5) Persist log
        log_row = self._persist_log(
            question=question,
            graph=graph,
            vector=vector,
            final_prompt=final_prompt,
            answer=answer_text,
            latency_ms=int((monotonic() - started) * 1000),
            error_message=None,
        )

        return QAOutcome(
            answer=answer_text,
            seed_entities=graph.seed_entities,
            triple_count=len(graph.triples),
            chunk_count=len(vector.chunks),
            query_log_id=log_row.id,
        )

    # ------------------------------------------------------------------
    def _persist_log(
        self,
        *,
        question,
        graph,
        vector,
        final_prompt: str,
        answer: str | None,
        latency_ms: int,
        error_message: str | None,
    ) -> AIQueryLog:
        row = AIQueryLog(
            question=question,
            detected_entities_json={"seed_entities": list(graph.seed_entities)},
            graph_context_json={
                "triples": [
                    {
                        "source": t.source,
                        "relation": t.relation,
                        "target": t.target,
                        "confidence": t.confidence,
                        "chunk_id": t.chunk_id,
                    }
                    for t in graph.triples
                ],
                "evidence_chunk_ids": list(graph.evidence_chunk_ids),
            },
            retrieved_chunks_json=[
                {
                    "chunk_id": c.chunk_id,
                    "document_id": c.document_id,
                    "source": c.source,
                    "score": c.score,
                }
                for c in vector.chunks
            ],
            final_prompt=final_prompt,
            answer=answer,
            model_provider=self.provider.provider_name,
            model_name=getattr(self.provider, "model_name", None),
            token_estimate=len(final_prompt) // 4,  # rough chars/4 estimate
            latency_ms=latency_ms,
            error_message=error_message,
        )
        self.query_log_repo.add(row)
        self.db.commit()
        return row
