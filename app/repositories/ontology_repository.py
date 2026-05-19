from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.ontology_entity_type import OntologyEntityType
from app.db.models.ontology_relation_type import OntologyRelationType


class OntologyRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ---- entity types ----
    def add_entity_type(self, et: OntologyEntityType) -> OntologyEntityType:
        self.db.add(et)
        self.db.flush()
        return et

    def get_entity_type(self, id_: UUID) -> OntologyEntityType | None:
        return self.db.get(OntologyEntityType, id_)

    def get_entity_type_by_name(self, name: str) -> OntologyEntityType | None:
        stmt = select(OntologyEntityType).where(OntologyEntityType.name == name)
        return self.db.execute(stmt).scalar_one_or_none()

    def list_entity_types(self, *, active_only: bool = False) -> list[OntologyEntityType]:
        stmt = select(OntologyEntityType).order_by(OntologyEntityType.name.asc())
        if active_only:
            stmt = stmt.where(OntologyEntityType.is_active.is_(True))
        return list(self.db.execute(stmt).scalars().all())

    # ---- relation types ----
    def add_relation_type(self, rt: OntologyRelationType) -> OntologyRelationType:
        self.db.add(rt)
        self.db.flush()
        return rt

    def get_relation_type(self, id_: UUID) -> OntologyRelationType | None:
        return self.db.get(OntologyRelationType, id_)

    def find_relation_type(
        self, source_type: str, relation_name: str, target_type: str
    ) -> OntologyRelationType | None:
        stmt = select(OntologyRelationType).where(
            OntologyRelationType.source_entity_type == source_type,
            OntologyRelationType.relation_name == relation_name,
            OntologyRelationType.target_entity_type == target_type,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list_relation_types(self, *, active_only: bool = False) -> list[OntologyRelationType]:
        stmt = select(OntologyRelationType).order_by(
            OntologyRelationType.source_entity_type.asc(),
            OntologyRelationType.relation_name.asc(),
            OntologyRelationType.target_entity_type.asc(),
        )
        if active_only:
            stmt = stmt.where(OntologyRelationType.is_active.is_(True))
        return list(self.db.execute(stmt).scalars().all())
