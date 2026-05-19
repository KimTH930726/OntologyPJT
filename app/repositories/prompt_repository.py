from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.prompt_template import PromptTemplate
from app.db.models.prompt_version import PromptVersion


class PromptRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ---- template ----
    def add_template(self, t: PromptTemplate) -> PromptTemplate:
        self.db.add(t)
        self.db.flush()
        return t

    def get_template(self, id_: UUID) -> PromptTemplate | None:
        return self.db.get(PromptTemplate, id_)

    def get_template_by_name(self, name: str) -> PromptTemplate | None:
        stmt = select(PromptTemplate).where(PromptTemplate.name == name)
        return self.db.execute(stmt).scalar_one_or_none()

    # ---- version ----
    def add_version(self, v: PromptVersion) -> PromptVersion:
        self.db.add(v)
        self.db.flush()
        return v

    def get_active_version(self, template_id: UUID) -> PromptVersion | None:
        stmt = (
            select(PromptVersion)
            .where(PromptVersion.template_id == template_id)
            .where(PromptVersion.is_active.is_(True))
            .limit(1)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_active_version_by_name(self, name: str) -> PromptVersion | None:
        tpl = self.get_template_by_name(name)
        if tpl is None:
            return None
        return self.get_active_version(tpl.id)
