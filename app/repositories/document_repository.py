from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.document import Document


class DocumentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, doc: Document) -> Document:
        self.db.add(doc)
        self.db.flush()
        return doc

    def get(self, document_id: UUID) -> Document | None:
        return self.db.get(Document, document_id)

    def find_by_content_hash(self, content_hash: str) -> Document | None:
        stmt = select(Document).where(Document.content_hash == content_hash)
        return self.db.execute(stmt).scalar_one_or_none()

    def list(
        self, *, domain: str | None = None, limit: int = 50, offset: int = 0
    ) -> list[Document]:
        stmt = select(Document).order_by(Document.created_at.desc()).limit(limit).offset(offset)
        if domain:
            stmt = stmt.where(Document.domain == domain)
        return list(self.db.execute(stmt).scalars().all())

    def count(self, *, domain: str | None = None) -> int:
        stmt = select(func.count(Document.id))
        if domain:
            stmt = stmt.where(Document.domain == domain)
        return self.db.execute(stmt).scalar_one()
