from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models.ontology_entity_type import OntologyEntityType
from app.db.models.ontology_relation_type import OntologyRelationType
from app.integrations.llm.base import EntityTypeSpec, OntologySnapshot, RelationTypeSpec
from app.repositories.ontology_repository import OntologyRepository
from app.schemas.ontology import (
    OntologyEntityTypeCreate,
    OntologyEntityTypeUpdate,
    OntologyRelationTypeCreate,
    OntologyRelationTypeUpdate,
)


class OntologySchemaService:
    """Manages entity/relation type registry and ontology validation."""

    def __init__(self, db: Session, repo: OntologyRepository | None = None) -> None:
        self.db = db
        self.repo = repo or OntologyRepository(db)

    # ---- entity types ----
    def create_entity_type(self, dto: OntologyEntityTypeCreate) -> OntologyEntityType:
        existing = self.repo.get_entity_type_by_name(dto.name)
        if existing is not None:
            return existing
        row = OntologyEntityType(
            name=dto.name,
            display_name=dto.display_name,
            description=dto.description,
            is_active=True,
        )
        return self.repo.add_entity_type(row)

    def update_entity_type(
        self, id_: UUID, dto: OntologyEntityTypeUpdate
    ) -> OntologyEntityType | None:
        row = self.repo.get_entity_type(id_)
        if row is None:
            return None
        if dto.display_name is not None:
            row.display_name = dto.display_name
        if dto.description is not None:
            row.description = dto.description
        if dto.is_active is not None:
            row.is_active = dto.is_active
        self.db.flush()
        return row

    def deactivate_entity_type(self, id_: UUID) -> OntologyEntityType | None:
        row = self.repo.get_entity_type(id_)
        if row is None:
            return None
        row.is_active = False
        self.db.flush()
        return row

    def list_entity_types(self, *, active_only: bool = False) -> list[OntologyEntityType]:
        return self.repo.list_entity_types(active_only=active_only)

    # ---- relation types ----
    def create_relation_type(self, dto: OntologyRelationTypeCreate) -> OntologyRelationType:
        existing = self.repo.find_relation_type(
            dto.source_entity_type, dto.relation_name, dto.target_entity_type
        )
        if existing is not None:
            return existing
        row = OntologyRelationType(
            source_entity_type=dto.source_entity_type,
            relation_name=dto.relation_name,
            target_entity_type=dto.target_entity_type,
            display_name=dto.display_name,
            description=dto.description,
            is_active=True,
        )
        return self.repo.add_relation_type(row)

    def update_relation_type(
        self, id_: UUID, dto: OntologyRelationTypeUpdate
    ) -> OntologyRelationType | None:
        row = self.repo.get_relation_type(id_)
        if row is None:
            return None
        if dto.display_name is not None:
            row.display_name = dto.display_name
        if dto.description is not None:
            row.description = dto.description
        if dto.is_active is not None:
            row.is_active = dto.is_active
        self.db.flush()
        return row

    def deactivate_relation_type(self, id_: UUID) -> OntologyRelationType | None:
        row = self.repo.get_relation_type(id_)
        if row is None:
            return None
        row.is_active = False
        self.db.flush()
        return row

    def list_relation_types(self, *, active_only: bool = False) -> list[OntologyRelationType]:
        return self.repo.list_relation_types(active_only=active_only)

    # ---- validation (used by extraction/review) ----
    def validate_entity_type(self, entity_type: str) -> bool:
        row = self.repo.get_entity_type_by_name(entity_type)
        return row is not None and row.is_active

    def validate_relation(self, source_type: str, relation: str, target_type: str) -> bool:
        row = self.repo.find_relation_type(source_type, relation, target_type)
        return row is not None and row.is_active

    def snapshot(self) -> OntologySnapshot:
        ets = self.repo.list_entity_types(active_only=True)
        rts = self.repo.list_relation_types(active_only=True)
        return OntologySnapshot(
            entity_types=tuple(EntityTypeSpec(name=e.name, description=e.description) for e in ets),
            relation_types=tuple(
                RelationTypeSpec(
                    source=r.source_entity_type,
                    relation=r.relation_name,
                    target=r.target_entity_type,
                    description=r.description,
                )
                for r in rts
            ),
        )
