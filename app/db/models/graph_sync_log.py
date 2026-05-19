from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class GraphSyncLog(Base):
    __tablename__ = "graph_sync_log"
    __table_args__ = (
        CheckConstraint("target_type IN ('ENTITY','RELATION')", name="ck_gsl_target_type"),
        CheckConstraint("sync_status IN ('SUCCESS','FAILED','SKIPPED')", name="ck_gsl_sync_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    target_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    target_id: Mapped[uuid.UUID] = mapped_column(Uuid(), nullable=False, index=True)
    sync_status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    neo4j_node_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    neo4j_relation_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
