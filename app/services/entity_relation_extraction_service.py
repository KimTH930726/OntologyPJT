from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models.document_chunk import DocumentChunk
from app.db.models.extracted_entity import ExtractedEntity
from app.db.models.extracted_relation import ExtractedRelation
from app.domain.enums import (
    SCHEMA_VIOLATION_RELATION_NOT_ALLOWED,
    SCHEMA_VIOLATION_UNKNOWN_ENTITY,
    AuditAction,
    CandidateSource,
    ReviewStatus,
)
from app.integrations.llm.base import LLMProvider
from app.integrations.llm.factory import get_llm_provider
from app.repositories.document_chunk_repository import DocumentChunkRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.extraction_repository import ExtractionRepository
from app.schemas.extraction import LLMEntityCandidate, LLMRelationCandidate
from app.services.audit_log_service import AuditLogService
from app.services.ontology_schema_service import OntologySchemaService

logger = logging.getLogger(__name__)


@dataclass
class ExtractionRunResult:
    document_id: UUID
    chunk_ids: list[UUID]
    entities_extracted: int
    relations_extracted: int
    schema_violations: int
    audit_log_id: UUID | None


class EntityRelationExtractionService:
    def __init__(
        self,
        db: Session,
        *,
        ontology: OntologySchemaService | None = None,
        provider: LLMProvider | None = None,
        document_repo: DocumentRepository | None = None,
        chunk_repo: DocumentChunkRepository | None = None,
        extraction_repo: ExtractionRepository | None = None,
        audit: AuditLogService | None = None,
    ) -> None:
        self.db = db
        self.ontology = ontology or OntologySchemaService(db)
        self.provider = provider or get_llm_provider()
        self.document_repo = document_repo or DocumentRepository(db)
        self.chunk_repo = chunk_repo or DocumentChunkRepository(db)
        self.extraction_repo = extraction_repo or ExtractionRepository(db)
        self.audit = audit or AuditLogService(db)

    # ---- public ----
    def extract_document(self, document_id: UUID) -> ExtractionRunResult:
        doc = self.document_repo.get(document_id)
        if doc is None:
            raise LookupError(f"document {document_id} not found")
        chunks = self.chunk_repo.list_by_document(document_id)
        return self._run(document_id=document_id, chunks=chunks, target_type="DOCUMENT")

    def extract_chunk(self, chunk_id: UUID) -> ExtractionRunResult:
        chunk = self.chunk_repo.get(chunk_id)
        if chunk is None:
            raise LookupError(f"chunk {chunk_id} not found")
        return self._run(document_id=chunk.document_id, chunks=[chunk], target_type="CHUNK")

    # ---- internal ----
    def _run(
        self,
        *,
        document_id: UUID,
        chunks: list[DocumentChunk],
        target_type: str,
    ) -> ExtractionRunResult:
        snapshot = self.ontology.snapshot()
        source_label = (
            CandidateSource.FAKE.value
            if self.provider.provider_name == "fake"
            else CandidateSource.LLM.value
        )

        total_entities = 0
        total_relations = 0
        total_violations = 0
        chunk_ids: list[UUID] = []

        for chunk in chunks:
            chunk_ids.append(chunk.id)
            response = self.provider.extract(chunk.text, snapshot)

            # 1) entities
            id_by_norm: dict[str, UUID] = {}
            for e in response.entities:
                entity, was_violation = self._save_entity(document_id, chunk.id, e, source_label)
                id_by_norm[e.normalized_name] = entity.id
                if was_violation:
                    total_violations += 1
                else:
                    total_entities += 1

            # 2) relations (auto-create referenced entities if missing)
            for r in response.relations:
                relation, was_violation = self._save_relation(
                    document_id, chunk.id, r, id_by_norm, source_label
                )
                if was_violation:
                    total_violations += 1
                else:
                    total_relations += 1

        self.db.flush()

        log = self.audit.log(
            action=AuditAction.EXTRACTION_RUN,
            actor=f"provider:{self.provider.provider_name}",
            target_type=target_type,
            target_id=chunks[0].id if target_type == "CHUNK" and chunks else document_id,
            document_id=document_id,
            chunk_id=chunks[0].id if target_type == "CHUNK" and chunks else None,
            metadata={
                "provider": self.provider.provider_name,
                "chunks_processed": len(chunks),
                "entities_extracted": total_entities,
                "relations_extracted": total_relations,
                "schema_violations": total_violations,
            },
        )
        self.db.commit()

        return ExtractionRunResult(
            document_id=document_id,
            chunk_ids=chunk_ids,
            entities_extracted=total_entities,
            relations_extracted=total_relations,
            schema_violations=total_violations,
            audit_log_id=log.id,
        )

    # ---- save helpers ----
    def _save_entity(
        self,
        document_id: UUID,
        chunk_id: UUID,
        e: LLMEntityCandidate,
        source_label: str,
    ) -> tuple[ExtractedEntity, bool]:
        is_violation = not self.ontology.validate_entity_type(e.type)
        row = ExtractedEntity(
            document_id=document_id,
            chunk_id=chunk_id,
            entity_type=e.type,
            name=e.name,
            normalized_name=e.normalized_name,
            confidence=e.confidence,
            evidence_text=e.evidence_text,
            source=source_label,
            review_status=(
                ReviewStatus.REJECTED.value if is_violation else ReviewStatus.PENDING.value
            ),
            rejection_reason=SCHEMA_VIOLATION_UNKNOWN_ENTITY if is_violation else None,
            reviewed_by="system" if is_violation else None,
            reviewed_at=datetime.now(UTC) if is_violation else None,
        )
        return self.extraction_repo.add_entity(row), is_violation

    def _resolve_entity_id(
        self,
        chunk_id: UUID,
        document_id: UUID,
        normalized_name: str,
        entity_type: str,
        id_by_norm: dict[str, UUID],
        source_label: str,
    ) -> UUID | None:
        """Try in-batch dict first, then DB lookup, otherwise auto-create a
        PENDING placeholder so the relation can be approved later by approving
        the referenced concept (e.g. ``Order``)."""
        if normalized_name in id_by_norm:
            return id_by_norm[normalized_name]
        existing = self.extraction_repo.find_pending_entity(chunk_id, normalized_name, entity_type)
        if existing is not None:
            id_by_norm[normalized_name] = existing.id
            return existing.id
        # entity_type may be invalid; if so we don't auto-create — relation
        # itself will be rejected as schema violation.
        if not self.ontology.validate_entity_type(entity_type):
            return None
        placeholder = ExtractedEntity(
            document_id=document_id,
            chunk_id=chunk_id,
            entity_type=entity_type,
            name=normalized_name,
            normalized_name=normalized_name,
            confidence=1.0,
            evidence_text="(auto-created from relation reference)",
            source=source_label,
            review_status=ReviewStatus.PENDING.value,
        )
        self.extraction_repo.add_entity(placeholder)
        id_by_norm[normalized_name] = placeholder.id
        return placeholder.id

    def _save_relation(
        self,
        document_id: UUID,
        chunk_id: UUID,
        r: LLMRelationCandidate,
        id_by_norm: dict[str, UUID],
        source_label: str,
    ) -> tuple[ExtractedRelation, bool]:
        # Resolve / placeholder-create entities before checking schema so we
        # don't pollute DB with violation relations that have null FKs.
        source_id = self._resolve_entity_id(
            chunk_id, document_id, r.source, r.source_type, id_by_norm, source_label
        )
        target_id = self._resolve_entity_id(
            chunk_id, document_id, r.target, r.target_type, id_by_norm, source_label
        )

        is_violation = not self.ontology.validate_relation(r.source_type, r.relation, r.target_type)
        row = ExtractedRelation(
            document_id=document_id,
            chunk_id=chunk_id,
            source_entity_id=source_id,
            source_entity_name=r.source,
            source_entity_type=r.source_type,
            relation_type=r.relation,
            target_entity_id=target_id,
            target_entity_name=r.target,
            target_entity_type=r.target_type,
            confidence=r.confidence,
            evidence_text=r.evidence_text,
            source=source_label,
            review_status=(
                ReviewStatus.REJECTED.value if is_violation else ReviewStatus.PENDING.value
            ),
            rejection_reason=(SCHEMA_VIOLATION_RELATION_NOT_ALLOWED if is_violation else None),
            reviewed_by="system" if is_violation else None,
            reviewed_at=datetime.now(UTC) if is_violation else None,
        )
        return self.extraction_repo.add_relation(row), is_violation
