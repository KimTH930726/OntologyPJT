"""Regression: QAService MUST always persist an ai_query_log row and MUST
fall back gracefully when graph/vector/LLM are missing."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from app.services.graph_retriever import GraphRetrievalResult, GraphTriple
from app.services.qa_service import LLMCallError, QAService
from app.services.vector_retriever import RetrievedChunk, VectorRetrievalResult


# ---------- doubles ----------
class _FakeGraphRetriever:
    def __init__(self, result: GraphRetrievalResult) -> None:
        self.result = result

    def retrieve(self, question: str, depth: int = 2) -> GraphRetrievalResult:  # noqa: ARG002
        return self.result


class _FakeVectorRetriever:
    def __init__(self, result: VectorRetrievalResult) -> None:
        self.result = result

    def retrieve(self, question: str, evidence_chunk_ids, top_k: int = 5) -> VectorRetrievalResult:  # noqa: ARG002
        return self.result


class _OkProvider:
    provider_name = "fake"
    model_name = "fake"

    def __init__(self) -> None:
        self.called_with: str | None = None

    def answer(self, prompt: str) -> str:
        self.called_with = prompt
        return "결론: ok"

    def extract_intent_entities(self, question: str) -> list[str]:  # noqa: ARG002
        return []


class _BoomProvider(_OkProvider):
    def answer(self, prompt: str) -> str:  # noqa: ARG002
        raise RuntimeError("provider outage")


@dataclass
class _Logs:
    rows: list = field(default_factory=list)

    def add(self, row):  # noqa: ANN001
        self.rows.append(row)
        return row


class _FakeSession:
    def __init__(self) -> None:
        self.commits = 0
        self.added: list = []

    def add(self, row) -> None:  # noqa: ANN001
        self.added.append(row)

    def commit(self) -> None:
        self.commits += 1

    def flush(self) -> None:
        pass


def _build(
    *,
    graph: GraphRetrievalResult,
    vector: VectorRetrievalResult,
    provider,
) -> tuple[QAService, _Logs, _FakeSession]:
    from app.services.context_builder import ContextBuilder

    session = _FakeSession()
    logs = _Logs()

    # PromptBuilder uses jinja2 templates; provide a tiny inline renderer
    class _Tpl:
        def build_qa(self, ctx, question, **_kw):  # noqa: ANN001
            return (
                "[Graph Context]\n"
                f"{ctx.graph_block}\n"
                "[Document Evidence]\n"
                f"{ctx.evidence_block}\n"
                "[User Question]\n"
                f"{question}\n"
            )

    svc = QAService(
        session,  # type: ignore[arg-type]
        graph_retriever=_FakeGraphRetriever(graph),  # type: ignore[arg-type]
        vector_retriever=_FakeVectorRetriever(vector),  # type: ignore[arg-type]
        context_builder=ContextBuilder(),
        prompt_builder=_Tpl(),  # type: ignore[arg-type]
        provider=provider,
        query_log_repo=logs,  # type: ignore[arg-type]
    )
    return svc, logs, session


@pytest.mark.unit
@pytest.mark.invariant
class TestQALogPersistence:
    """Invariant 5: every QA request creates exactly one ai_query_log row."""

    def test_no_context_path_persists_log_without_calling_llm(self) -> None:
        provider = _OkProvider()
        svc, logs, _ = _build(
            graph=GraphRetrievalResult(),
            vector=VectorRetrievalResult(),
            provider=provider,
        )
        outcome = svc.answer("아무 질문이나")
        assert provider.called_with is None  # LLM skipped
        assert len(logs.rows) == 1
        assert logs.rows[0].error_message is None
        assert "근거 부족" in outcome.answer

    def test_happy_path_persists_log_with_answer(self) -> None:
        provider = _OkProvider()
        svc, logs, _ = _build(
            graph=GraphRetrievalResult(
                seed_entities=["FullCancelPolicy"],
                triples=[GraphTriple("FullCancelPolicy", "REQUIRES", "PaymentCompleted", 0.9)],
                evidence_chunk_ids=["c1"],
            ),
            vector=VectorRetrievalResult(
                chunks=[RetrievedChunk("c1", "d1", "원문", "graph_evidence")]
            ),
            provider=provider,
        )
        outcome = svc.answer("환불 가능한가?")
        assert provider.called_with is not None
        assert outcome.answer == "결론: ok"
        assert len(logs.rows) == 1
        row = logs.rows[0]
        assert row.answer == "결론: ok"
        assert row.error_message is None
        assert "FullCancelPolicy" in row.final_prompt
        assert row.detected_entities_json == {"seed_entities": ["FullCancelPolicy"]}

    def test_llm_failure_persists_log_and_raises(self) -> None:
        provider = _BoomProvider()
        svc, logs, _ = _build(
            graph=GraphRetrievalResult(
                triples=[GraphTriple("A", "REQUIRES", "B", 0.9)],
            ),
            vector=VectorRetrievalResult(
                chunks=[RetrievedChunk("c1", "d1", "원문", "graph_evidence")]
            ),
            provider=provider,
        )
        with pytest.raises(LLMCallError) as exc:
            svc.answer("질문")
        # Log is still persisted, with error_message set.
        assert len(logs.rows) == 1
        assert logs.rows[0].error_message is not None
        assert "provider outage" in logs.rows[0].error_message
        assert exc.value.query_log_id == logs.rows[0].id


@pytest.mark.unit
@pytest.mark.invariant
class TestQAVectorOnlyFallback:
    """Invariant 6: when graph context is empty but vector chunks exist,
    we still call the LLM with evidence-only context."""

    def test_vector_only_still_calls_llm(self) -> None:
        provider = _OkProvider()
        svc, logs, _ = _build(
            graph=GraphRetrievalResult(),  # empty
            vector=VectorRetrievalResult(
                chunks=[RetrievedChunk("c1", "d1", "원문 텍스트", "vector_search", score=0.7)]
            ),
            provider=provider,
        )
        outcome = svc.answer("배송이란?")
        assert provider.called_with is not None
        # graph block was "(없음)" but evidence block had content
        assert "(없음)" in provider.called_with  # graph empty marker
        assert "원문 텍스트" in provider.called_with
        assert outcome.answer == "결론: ok"
        assert len(logs.rows) == 1
