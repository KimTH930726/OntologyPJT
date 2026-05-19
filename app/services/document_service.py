from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models.document import Document
from app.db.models.document_chunk import DocumentChunk
from app.domain.enums import VectorStatus
from app.repositories.document_chunk_repository import DocumentChunkRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.qdrant_repository import QdrantRepository
from app.services.chunk_embedding_service import ChunkEmbeddingService
from app.services.chunking_service import ChunkingService
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class DuplicateDocumentError(Exception):
    def __init__(self, existing_id: UUID) -> None:
        super().__init__(f"document with same content already exists: {existing_id}")
        self.existing_id = existing_id


@dataclass
class DocumentCreationResult:
    document: Document
    chunk_count: int
    aggregate_status: VectorStatus


class DocumentService:
    def __init__(
        self,
        db: Session,
        document_repo: DocumentRepository | None = None,
        chunk_repo: DocumentChunkRepository | None = None,
        chunking: ChunkingService | None = None,
        chunk_embedding: ChunkEmbeddingService | None = None,
    ) -> None:
        self.db = db
        self.document_repo = document_repo or DocumentRepository(db)
        self.chunk_repo = chunk_repo or DocumentChunkRepository(db)
        self.chunking = chunking or ChunkingService()
        self.chunk_embedding = chunk_embedding or ChunkEmbeddingService(
            chunk_repo=self.chunk_repo,
            qdrant_repo=QdrantRepository(),
            embedder=EmbeddingService(),
        )

    # ---- queries ----
    def get(self, document_id: UUID) -> Document | None:
        return self.document_repo.get(document_id)

    def list(self, *, domain: str | None, limit: int, offset: int) -> tuple[list[Document], int]:
        items = self.document_repo.list(domain=domain, limit=limit, offset=offset)
        total = self.document_repo.count(domain=domain)
        return items, total

    def aggregate_status(self, document_id: UUID) -> tuple[int, VectorStatus]:
        total = self.chunk_repo.count_by_document(document_id)
        if total == 0:
            return 0, VectorStatus.PENDING
        counts = self.chunk_repo.status_counts_by_document(document_id)
        if counts.get(VectorStatus.FAILED.value, 0) > 0:
            return total, VectorStatus.FAILED
        if counts.get(VectorStatus.INDEXED.value, 0) == total:
            return total, VectorStatus.INDEXED
        return total, VectorStatus.PENDING

    def list_chunks(self, document_id: UUID) -> list[DocumentChunk]:
        return self.chunk_repo.list_by_document(document_id)

    # ---- command ----
    def create_document(
        self,
        *,
        title: str,
        domain: str,
        source_type: str,
        version: str,
        access_level: str,
        content: str,
    ) -> DocumentCreationResult:
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        existing = self.document_repo.find_by_content_hash(content_hash)
        if existing is not None:
            raise DuplicateDocumentError(existing.id)

        doc = Document(
            title=title,
            domain=domain,
            source_type=source_type,
            version=version,
            access_level=access_level,
            content_hash=content_hash,
        )
        self.document_repo.add(doc)

        drafts = self.chunking.split(content)
        chunks: list[DocumentChunk] = [
            DocumentChunk(
                document_id=doc.id,
                chunk_index=d.index,
                text=d.text,
                token_count=d.token_count,
                text_hash=hashlib.sha256(d.text.encode("utf-8")).hexdigest(),
                vector_status=VectorStatus.PENDING.value,
            )
            for d in drafts
        ]
        if chunks:
            self.chunk_repo.bulk_add(chunks)

        # Commit metadata before talking to Qdrant so partial failures keep
        # the document + PENDING chunks visible.
        self.db.commit()
        self.db.refresh(doc)

        result = self.chunk_embedding.index_document_chunks(doc, chunks)
        self.db.commit()
        self.db.refresh(doc)

        logger.info(
            "document created id=%s chunks=%d indexed=%d failed=%d",
            doc.id, result.total, result.indexed, result.failed,
        )

        return DocumentCreationResult(
            document=doc,
            chunk_count=result.total,
            aggregate_status=result.aggregate_status,
        )
