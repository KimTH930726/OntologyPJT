from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.graph_sync_log import GraphSyncLog


class GraphSyncLogRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, log: GraphSyncLog) -> GraphSyncLog:
        self.db.add(log)
        self.db.flush()
        return log

    def get(self, id_: UUID) -> GraphSyncLog | None:
        return self.db.get(GraphSyncLog, id_)

    def has_success(self, target_type: str, target_id: UUID) -> bool:
        stmt = (
            select(GraphSyncLog.id)
            .where(
                GraphSyncLog.target_type == target_type,
                GraphSyncLog.target_id == target_id,
                GraphSyncLog.sync_status == "SUCCESS",
            )
            .limit(1)
        )
        return self.db.execute(stmt).first() is not None

    def list(
        self,
        *,
        target_type: str | None = None,
        target_id: UUID | None = None,
        sync_status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[GraphSyncLog]:
        stmt = select(GraphSyncLog).order_by(GraphSyncLog.created_at.desc())
        if target_type is not None:
            stmt = stmt.where(GraphSyncLog.target_type == target_type)
        if target_id is not None:
            stmt = stmt.where(GraphSyncLog.target_id == target_id)
        if sync_status is not None:
            stmt = stmt.where(GraphSyncLog.sync_status == sync_status)
        stmt = stmt.limit(limit).offset(offset)
        return list(self.db.execute(stmt).scalars().all())
