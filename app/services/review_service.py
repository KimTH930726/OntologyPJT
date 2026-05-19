from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models.extracted_entity import ExtractedEntity
from app.db.models.extracted_relation import ExtractedRelation
from app.domain.enums import AuditAction, GraphSyncTargetType, ReviewStatus
from app.domain.exceptions import ConflictError, DomainError, NotFoundError, ValidationError
from app.domain.policies.relation_approval import (
    RelationApprovalCode,
    evaluate_relation_approval,
)
from app.repositories.extraction_repository import ExtractionRepository
from app.schemas.review import (
    ReviewApproveRequest,
    ReviewMergeRequest,
    ReviewModifyEntityRequest,
    ReviewModifyRelationRequest,
    ReviewRejectRequest,
)
from app.services.audit_log_service import (
    AuditLogService,
    entity_snapshot,
    relation_snapshot,
)

logger = logging.getLogger(__name__)


# Backward-compatible alias kept while routes still import ReviewError.
ReviewError = DomainError


class SourceNotApprovedError(ConflictError):
    code = RelationApprovalCode.SOURCE_NOT_APPROVED


class TargetNotApprovedError(ConflictError):
    code = RelationApprovalCode.TARGET_NOT_APPROVED


__all__ = [
    "ReviewError",
    "DomainError",
    "ConflictError",
    "NotFoundError",
    "ValidationError",
    "SourceNotApprovedError",
    "TargetNotApprovedError",
    "ReviewService",
]


def _utcnow() -> datetime:
    return datetime.now(UTC)


class ReviewService:
    def __init__(
        self,
        db: Session,
        *,
        repo: ExtractionRepository | None = None,
        audit: AuditLogService | None = None,
    ) -> None:
        self.db = db
        self.repo = repo or ExtractionRepository(db)
        self.audit = audit or AuditLogService(db)

    # =================== ENTITY ===================
    def approve_entity(self, entity_id: UUID, dto: ReviewApproveRequest) -> ExtractedEntity:
        e = self._get_entity_or_raise(entity_id)
        before = entity_snapshot(e)
        e.review_status = ReviewStatus.APPROVED.value
        e.reviewed_by = dto.reviewer
        e.reviewed_at = _utcnow()
        e.rejection_reason = None
        self.db.flush()
        self.audit.log(
            action=AuditAction.ENTITY_APPROVED,
            actor=dto.reviewer,
            target_type="ENTITY",
            target_id=e.id,
            document_id=e.document_id,
            chunk_id=e.chunk_id,
            before=before,
            after=entity_snapshot(e),
        )
        self.db.commit()
        self._maybe_auto_sync(target_type=GraphSyncTargetType.ENTITY)
        return e

    def reject_entity(self, entity_id: UUID, dto: ReviewRejectRequest) -> ExtractedEntity:
        e = self._get_entity_or_raise(entity_id)
        before = entity_snapshot(e)
        e.review_status = ReviewStatus.REJECTED.value
        e.reviewed_by = dto.reviewer
        e.reviewed_at = _utcnow()
        e.rejection_reason = dto.reason
        self.db.flush()
        self.audit.log(
            action=AuditAction.ENTITY_REJECTED,
            actor=dto.reviewer,
            target_type="ENTITY",
            target_id=e.id,
            document_id=e.document_id,
            chunk_id=e.chunk_id,
            before=before,
            after=entity_snapshot(e),
        )
        self.db.commit()
        return e

    def modify_entity(self, entity_id: UUID, dto: ReviewModifyEntityRequest) -> ExtractedEntity:
        e = self._get_entity_or_raise(entity_id)
        before = entity_snapshot(e)
        if dto.name is not None:
            e.name = dto.name
        if dto.normalized_name is not None:
            e.normalized_name = dto.normalized_name
        if dto.entity_type is not None:
            e.entity_type = dto.entity_type
        e.review_status = ReviewStatus.MODIFIED.value
        e.reviewed_by = dto.reviewer
        e.reviewed_at = _utcnow()
        self.db.flush()
        self.audit.log(
            action=AuditAction.ENTITY_MODIFIED,
            actor=dto.reviewer,
            target_type="ENTITY",
            target_id=e.id,
            document_id=e.document_id,
            chunk_id=e.chunk_id,
            before=before,
            after=entity_snapshot(e),
        )
        self.db.commit()
        return e

    def merge_entity(self, entity_id: UUID, dto: ReviewMergeRequest) -> ExtractedEntity:
        e = self._get_entity_or_raise(entity_id)
        target = self.repo.get_entity(dto.into_id)
        if target is None:
            raise NotFoundError(f"merge target entity {dto.into_id} not found")
        if target.id == e.id:
            raise ReviewError("cannot merge entity into itself", code="VALIDATION_ERROR")
        before = entity_snapshot(e)
        e.merged_into_id = target.id
        e.review_status = ReviewStatus.MERGED.value
        e.reviewed_by = dto.reviewer
        e.reviewed_at = _utcnow()
        self.db.flush()
        self.audit.log(
            action=AuditAction.ENTITY_MERGED,
            actor=dto.reviewer,
            target_type="ENTITY",
            target_id=e.id,
            document_id=e.document_id,
            chunk_id=e.chunk_id,
            before=before,
            after=entity_snapshot(e),
            metadata={"merged_into_id": str(target.id)},
        )
        self.db.commit()
        return e

    # =================== RELATION ===================
    def approve_relation(self, relation_id: UUID, dto: ReviewApproveRequest) -> ExtractedRelation:
        r = self._get_relation_or_raise(relation_id)
        # Guard: source/target entities must both be APPROVED.
        self._assert_relation_endpoints_approved(r)
        before = relation_snapshot(r)
        r.review_status = ReviewStatus.APPROVED.value
        r.reviewed_by = dto.reviewer
        r.reviewed_at = _utcnow()
        r.rejection_reason = None
        self.db.flush()
        self.audit.log(
            action=AuditAction.RELATION_APPROVED,
            actor=dto.reviewer,
            target_type="RELATION",
            target_id=r.id,
            document_id=r.document_id,
            chunk_id=r.chunk_id,
            before=before,
            after=relation_snapshot(r),
        )
        self.db.commit()
        self._maybe_auto_sync(target_type=GraphSyncTargetType.RELATION)
        return r

    def reject_relation(self, relation_id: UUID, dto: ReviewRejectRequest) -> ExtractedRelation:
        r = self._get_relation_or_raise(relation_id)
        before = relation_snapshot(r)
        r.review_status = ReviewStatus.REJECTED.value
        r.reviewed_by = dto.reviewer
        r.reviewed_at = _utcnow()
        r.rejection_reason = dto.reason
        self.db.flush()
        self.audit.log(
            action=AuditAction.RELATION_REJECTED,
            actor=dto.reviewer,
            target_type="RELATION",
            target_id=r.id,
            document_id=r.document_id,
            chunk_id=r.chunk_id,
            before=before,
            after=relation_snapshot(r),
        )
        self.db.commit()
        return r

    def modify_relation(
        self, relation_id: UUID, dto: ReviewModifyRelationRequest
    ) -> ExtractedRelation:
        r = self._get_relation_or_raise(relation_id)
        before = relation_snapshot(r)
        if dto.relation_type is not None:
            r.relation_type = dto.relation_type
        if dto.source_entity_name is not None:
            r.source_entity_name = dto.source_entity_name
        if dto.source_entity_type is not None:
            r.source_entity_type = dto.source_entity_type
        if dto.target_entity_name is not None:
            r.target_entity_name = dto.target_entity_name
        if dto.target_entity_type is not None:
            r.target_entity_type = dto.target_entity_type
        r.review_status = ReviewStatus.MODIFIED.value
        r.reviewed_by = dto.reviewer
        r.reviewed_at = _utcnow()
        self.db.flush()
        self.audit.log(
            action=AuditAction.RELATION_MODIFIED,
            actor=dto.reviewer,
            target_type="RELATION",
            target_id=r.id,
            document_id=r.document_id,
            chunk_id=r.chunk_id,
            before=before,
            after=relation_snapshot(r),
        )
        self.db.commit()
        return r

    def merge_relation(self, relation_id: UUID, dto: ReviewMergeRequest) -> ExtractedRelation:
        r = self._get_relation_or_raise(relation_id)
        if self.repo.get_relation(dto.into_id) is None:
            raise NotFoundError(f"merge target relation {dto.into_id} not found")
        if dto.into_id == r.id:
            raise ReviewError("cannot merge relation into itself", code="VALIDATION_ERROR")
        before = relation_snapshot(r)
        r.review_status = ReviewStatus.MERGED.value
        r.reviewed_by = dto.reviewer
        r.reviewed_at = _utcnow()
        self.db.flush()
        self.audit.log(
            action=AuditAction.RELATION_MERGED,
            actor=dto.reviewer,
            target_type="RELATION",
            target_id=r.id,
            document_id=r.document_id,
            chunk_id=r.chunk_id,
            before=before,
            after=relation_snapshot(r),
            metadata={"merged_into_id": str(dto.into_id)},
        )
        self.db.commit()
        return r

    # =================== internals ===================
    def _get_entity_or_raise(self, id_: UUID) -> ExtractedEntity:
        row = self.repo.get_entity(id_)
        if row is None:
            raise NotFoundError(f"entity {id_} not found")
        return row

    def _get_relation_or_raise(self, id_: UUID) -> ExtractedRelation:
        row = self.repo.get_relation(id_)
        if row is None:
            raise NotFoundError(f"relation {id_} not found")
        return row

    def _assert_relation_endpoints_approved(self, r: ExtractedRelation) -> None:
        src = self._resolve_relation_endpoint(
            r.source_entity_id, r.chunk_id, r.source_entity_name, r.source_entity_type
        )
        tgt = self._resolve_relation_endpoint(
            r.target_entity_id, r.chunk_id, r.target_entity_name, r.target_entity_type
        )
        ok, reason = evaluate_relation_approval(src, tgt)
        if not ok:
            if reason == RelationApprovalCode.SOURCE_NOT_APPROVED:
                raise SourceNotApprovedError("source entity is not APPROVED — approve it first")
            raise TargetNotApprovedError("target entity is not APPROVED — approve it first")
        if src is not None and r.source_entity_id != src.id:
            r.source_entity_id = src.id
        if tgt is not None and r.target_entity_id != tgt.id:
            r.target_entity_id = tgt.id

    def _maybe_auto_sync(self, *, target_type: GraphSyncTargetType) -> None:
        """Best-effort sync after approval. Disabled by default; failures are
        swallowed so that approval semantics never depend on Neo4j health."""
        if not get_settings().auto_graph_sync_on_approve:
            return
        try:
            # Local import to avoid a hard dependency cycle at module import.
            from app.services.graph_sync_service import GraphSyncService

            svc = GraphSyncService(self.db)
            if target_type == GraphSyncTargetType.ENTITY:
                svc.sync_approved_entities()
            else:
                svc.sync_all()
        except Exception as e:
            logger.warning("auto graph sync skipped: %s", e)

    def _resolve_relation_endpoint(
        self,
        existing_id: UUID | None,
        chunk_id: UUID,
        name: str,
        entity_type: str,
    ) -> ExtractedEntity | None:
        if existing_id is not None:
            e = self.repo.get_entity(existing_id)
            if e is not None:
                return e
        # Fallback: look up by (chunk_id, normalized_name, entity_type)
        return self.repo.find_pending_entity(chunk_id, name, entity_type)
