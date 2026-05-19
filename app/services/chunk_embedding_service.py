from __future__ import annotations

import logging
from dataclasses import dataclass

from app.db.models.document import Document
from app.db.models.document_chunk import DocumentChunk
from app.domain.enums import VectorStatus
from app.repositories.document_chunk_repository import DocumentChunkRepository
from app.repositories.qdrant_repository import QdrantRepository
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


@dataclass
class ChunkIndexingResult:
    total: int
    indexed: int
    failed: int

    @property
    def aggregate_status(self) -> VectorStatus:
        if self.total == 0:
            return VectorStatus.PENDING
        if self.failed > 0:
            return VectorStatus.FAILED
        if self.indexed == self.total:
            return VectorStatus.INDEXED
        return VectorStatus.PENDING


class ChunkEmbeddingService:
    """Generates fake embeddings for chunks and upserts them into Qdrant."""

    def __init__(
        self,
        chunk_repo: DocumentChunkRepository,
        qdrant_repo: QdrantRepository,
        embedder: EmbeddingService,
    ) -> None:
        self.chunk_repo = chunk_repo
        self.qdrant_repo = qdrant_repo
        self.embedder = embedder

    def index_document_chunks(
        self, document: Document, chunks: list[DocumentChunk]
    ) -> ChunkIndexingResult:
        indexed = 0
        failed = 0

        # Ensure collection once before the loop.
        self.qdrant_repo.ensure_collection()

        for chunk in chunks:
            try:
                vector = self.embedder.embed(chunk.text)
                payload = {
                    "chunk_id": str(chunk.id),
                    "document_id": str(document.id),
                    "domain": document.domain,
                    "version": document.version,
                    "access_level": document.access_level,
                    "source_type": document.source_type,
                    "text": chunk.text,
                }
                self.qdrant_repo.upsert_point(
                    point_id=str(chunk.id),
                    vector=vector,
                    payload=payload,
                )
                self.chunk_repo.mark_status(
                    chunk.id, VectorStatus.INDEXED, qdrant_point_id=str(chunk.id)
                )
                indexed += 1
            except Exception as e:
                logger.exception("embedding/upsert failed for chunk %s: %s", chunk.id, e)
                self.chunk_repo.mark_status(chunk.id, VectorStatus.FAILED)
                failed += 1

        return ChunkIndexingResult(total=len(chunks), indexed=indexed, failed=failed)
