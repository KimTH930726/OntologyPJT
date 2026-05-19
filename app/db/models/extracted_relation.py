from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.domain.enums import ReviewStatus


class ExtractedRelation(Base):
    __tablename__ = "extracted_relation"
    __table_args__ = (
        CheckConstraint(
            "review_status IN ('PENDING','APPROVED','REJECTED','MODIFIED','MERGED')",
            name="ck_extracted_relation_review_status",
        ),
        CheckConstraint(
            "source IN ('LLM','FAKE','MANUAL')",
            name="ck_extracted_relation_source",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("document.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("document_chunk.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    source_entity_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(),
        ForeignKey("extracted_entity.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_entity_name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    relation_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    target_entity_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(),
        ForeignKey("extracted_entity.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    target_entity_name: Mapped[str] = mapped_column(String(200), nullable=False)
    target_entity_type: Mapped[str] = mapped_column(String(100), nullable=False)

    confidence: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False, default=0)
    evidence_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="FAKE")
    review_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ReviewStatus.PENDING.value, index=True
    )
    reviewed_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
