from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.extracted_entity import ExtractedEntity
from app.db.models.extracted_relation import ExtractedRelation


class ExtractionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ---- entities ----
    def add_entity(self, entity: ExtractedEntity) -> ExtractedEntity:
        self.db.add(entity)
        self.db.flush()
        return entity

    def get_entity(self, id_: UUID) -> ExtractedEntity | None:
        return self.db.get(ExtractedEntity, id_)

    def find_pending_entity(
        self, chunk_id: UUID, normalized_name: str, entity_type: str
    ) -> ExtractedEntity | None:
        stmt = select(ExtractedEntity).where(
            ExtractedEntity.chunk_id == chunk_id,
            ExtractedEntity.normalized_name == normalized_name,
            ExtractedEntity.entity_type == entity_type,
            ExtractedEntity.review_status.in_(("PENDING", "APPROVED", "MODIFIED")),
        )
        return self.db.execute(stmt).scalars().first()

    def list_entities(
        self,
        *,
        document_id: UUID | None = None,
        chunk_id: UUID | None = None,
        review_status: str | None = None,
        entity_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ExtractedEntity]:
        stmt = select(ExtractedEntity).order_by(ExtractedEntity.created_at.asc())
        if document_id is not None:
            stmt = stmt.where(ExtractedEntity.document_id == document_id)
        if chunk_id is not None:
            stmt = stmt.where(ExtractedEntity.chunk_id == chunk_id)
        if review_status is not None:
            stmt = stmt.where(ExtractedEntity.review_status == review_status)
        if entity_type is not None:
            stmt = stmt.where(ExtractedEntity.entity_type == entity_type)
        stmt = stmt.limit(limit).offset(offset)
        return list(self.db.execute(stmt).scalars().all())

    # ---- relations ----
    def add_relation(self, relation: ExtractedRelation) -> ExtractedRelation:
        self.db.add(relation)
        self.db.flush()
        return relation

    def get_relation(self, id_: UUID) -> ExtractedRelation | None:
        return self.db.get(ExtractedRelation, id_)

    def list_relations(
        self,
        *,
        document_id: UUID | None = None,
        chunk_id: UUID | None = None,
        review_status: str | None = None,
        relation_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ExtractedRelation]:
        stmt = select(ExtractedRelation).order_by(ExtractedRelation.created_at.asc())
        if document_id is not None:
            stmt = stmt.where(ExtractedRelation.document_id == document_id)
        if chunk_id is not None:
            stmt = stmt.where(ExtractedRelation.chunk_id == chunk_id)
        if review_status is not None:
            stmt = stmt.where(ExtractedRelation.review_status == review_status)
        if relation_type is not None:
            stmt = stmt.where(ExtractedRelation.relation_type == relation_type)
        stmt = stmt.limit(limit).offset(offset)
        return list(self.db.execute(stmt).scalars().all())
