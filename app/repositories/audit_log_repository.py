from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.audit_log import AuditLog


class AuditLogRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, log: AuditLog) -> AuditLog:
        self.db.add(log)
        self.db.flush()
        return log

    def get(self, id_: UUID) -> AuditLog | None:
        return self.db.get(AuditLog, id_)

    def list(
        self,
        *,
        action: str | None = None,
        target_type: str | None = None,
        target_id: UUID | None = None,
        document_id: UUID | None = None,
        chunk_id: UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLog]:
        stmt = select(AuditLog).order_by(AuditLog.created_at.desc())
        if action is not None:
            stmt = stmt.where(AuditLog.action == action)
        if target_type is not None:
            stmt = stmt.where(AuditLog.target_type == target_type)
        if target_id is not None:
            stmt = stmt.where(AuditLog.target_id == target_id)
        if document_id is not None:
            stmt = stmt.where(AuditLog.document_id == document_id)
        if chunk_id is not None:
            stmt = stmt.where(AuditLog.chunk_id == chunk_id)
        stmt = stmt.limit(limit).offset(offset)
        return list(self.db.execute(stmt).scalars().all())
