from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.repositories.document_chunk_repository import DocumentChunkRepository
from app.repositories.qdrant_repository import QdrantRepository
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    chunk_id: str
    document_id: str
    text: str
    source: str  # "graph_evidence" | "vector_search"
    score: float | None = None


@dataclass
class VectorRetrievalResult:
    chunks: list[RetrievedChunk] = field(default_factory=list)


class VectorRetriever:
    """Returns graph-evidence chunks first, then non-duplicate vector hits."""

    def __init__(
        self,
        db: Session,
        *,
        embedder: EmbeddingService | None = None,
        qdrant_repo: QdrantRepository | None = None,
        chunk_repo: DocumentChunkRepository | None = None,
    ) -> None:
        self.db = db
        self.embedder = embedder or EmbeddingService()
        self.qdrant = qdrant_repo or QdrantRepository()
        self.chunk_repo = chunk_repo or DocumentChunkRepository(db)

    def retrieve(
        self,
        question: str,
        evidence_chunk_ids: list[str],
        top_k: int = 5,
    ) -> VectorRetrievalResult:
        retrieved: list[RetrievedChunk] = []
        seen: set[str] = set()

        # 1) Graph evidence chunks (Postgres direct lookup)
        if evidence_chunk_ids:
            uuid_ids = _safe_uuids(evidence_chunk_ids)
            for chunk in self.chunk_repo.get_many(uuid_ids):
                cid = str(chunk.id)
                if cid in seen:
                    continue
                seen.add(cid)
                retrieved.append(
                    RetrievedChunk(
                        chunk_id=cid,
                        document_id=str(chunk.document_id),
                        text=chunk.text,
                        source="graph_evidence",
                    )
                )

        # 2) Free vector search to top up
        remaining = max(top_k - len(retrieved), 0)
        if remaining > 0:
            try:
                vector = self.embedder.embed(question)
                results = self.qdrant.search(vector=vector, top_k=top_k + len(retrieved))
            except Exception as e:
                logger.warning("vector search failed: %s", e)
                results = []
            for hit in results:
                cid = str(hit["id"])
                if cid in seen:
                    continue
                seen.add(cid)
                payload = hit.get("payload") or {}
                retrieved.append(
                    RetrievedChunk(
                        chunk_id=cid,
                        document_id=str(payload.get("document_id", "")),
                        text=str(payload.get("text", "")),
                        source="vector_search",
                        score=float(hit.get("score", 0.0)),
                    )
                )
                if len(retrieved) - len(_evidence_in(retrieved)) >= remaining:
                    break

        return VectorRetrievalResult(chunks=retrieved[: top_k + len(evidence_chunk_ids)])


def _safe_uuids(values: list[str]) -> list[uuid.UUID]:
    out: list[uuid.UUID] = []
    for v in values:
        try:
            out.append(uuid.UUID(v))
        except (ValueError, TypeError):
            continue
    return out


def _evidence_in(chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
    return [c for c in chunks if c.source == "graph_evidence"]
