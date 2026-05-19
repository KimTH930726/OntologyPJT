from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.ai_query_log import AIQueryLog


class AIQueryLogRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, row: AIQueryLog) -> AIQueryLog:
        self.db.add(row)
        self.db.flush()
        return row

    def get(self, id_: UUID) -> AIQueryLog | None:
        return self.db.get(AIQueryLog, id_)

    def list(
        self,
        *,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        contains_question: str | None = None,
        model_provider: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AIQueryLog]:
        stmt = select(AIQueryLog).order_by(AIQueryLog.created_at.desc())
        if created_from is not None:
            stmt = stmt.where(AIQueryLog.created_at >= created_from)
        if created_to is not None:
            stmt = stmt.where(AIQueryLog.created_at <= created_to)
        if contains_question:
            stmt = stmt.where(AIQueryLog.question.ilike(f"%{contains_question}%"))
        if model_provider:
            stmt = stmt.where(AIQueryLog.model_provider == model_provider)
        stmt = stmt.limit(limit).offset(offset)
        return list(self.db.execute(stmt).scalars().all())
