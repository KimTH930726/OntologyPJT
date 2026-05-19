from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.document_chunk import DocumentChunk
from app.domain.enums import VectorStatus


class DocumentChunkRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def bulk_add(self, chunks: Iterable[DocumentChunk]) -> list[DocumentChunk]:
        items = list(chunks)
        self.db.add_all(items)
        self.db.flush()
        return items

    def get(self, chunk_id: UUID) -> DocumentChunk | None:
        return self.db.get(DocumentChunk, chunk_id)

    def get_many(self, chunk_ids: list[UUID]) -> list[DocumentChunk]:
        if not chunk_ids:
            return []
        stmt = select(DocumentChunk).where(DocumentChunk.id.in_(chunk_ids))
        rows = list(self.db.execute(stmt).scalars().all())
        order = {cid: i for i, cid in enumerate(chunk_ids)}
        return sorted(rows, key=lambda r: order.get(r.id, 1_000_000))

    def list_by_document(self, document_id: UUID) -> list[DocumentChunk]:
        stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index.asc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def count_by_document(self, document_id: UUID) -> int:
        stmt = select(func.count(DocumentChunk.id)).where(DocumentChunk.document_id == document_id)
        return self.db.execute(stmt).scalar_one()

    def status_counts_by_document(self, document_id: UUID) -> dict[str, int]:
        stmt = (
            select(DocumentChunk.vector_status, func.count(DocumentChunk.id))
            .where(DocumentChunk.document_id == document_id)
            .group_by(DocumentChunk.vector_status)
        )
        return {status: cnt for status, cnt in self.db.execute(stmt).all()}

    def mark_status(
        self,
        chunk_id: UUID,
        status: VectorStatus,
        qdrant_point_id: str | None = None,
    ) -> None:
        chunk = self.db.get(DocumentChunk, chunk_id)
        if chunk is None:
            return
        chunk.vector_status = status.value
        if qdrant_point_id is not None:
            chunk.qdrant_point_id = qdrant_point_id
        self.db.flush()
