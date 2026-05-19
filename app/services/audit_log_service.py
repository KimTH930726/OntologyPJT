from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models.audit_log import AuditLog
from app.db.models.extracted_entity import ExtractedEntity
from app.db.models.extracted_relation import ExtractedRelation
from app.domain.enums import AuditAction
from app.repositories.audit_log_repository import AuditLogRepository


def _json_safe(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def entity_snapshot(entity: ExtractedEntity) -> dict[str, Any]:
    return {
        "id": _json_safe(entity.id),
        "document_id": _json_safe(entity.document_id),
        "chunk_id": _json_safe(entity.chunk_id),
        "entity_type": entity.entity_type,
        "name": entity.name,
        "normalized_name": entity.normalized_name,
        "confidence": _json_safe(entity.confidence),
        "review_status": entity.review_status,
        "rejection_reason": entity.rejection_reason,
        "reviewed_by": entity.reviewed_by,
        "reviewed_at": _json_safe(entity.reviewed_at),
        "merged_into_id": _json_safe(entity.merged_into_id),
        "source": entity.source,
    }


def relation_snapshot(relation: ExtractedRelation) -> dict[str, Any]:
    return {
        "id": _json_safe(relation.id),
        "document_id": _json_safe(relation.document_id),
        "chunk_id": _json_safe(relation.chunk_id),
        "source_entity_id": _json_safe(relation.source_entity_id),
        "source_entity_name": relation.source_entity_name,
        "source_entity_type": relation.source_entity_type,
        "relation_type": relation.relation_type,
        "target_entity_id": _json_safe(relation.target_entity_id),
        "target_entity_name": relation.target_entity_name,
        "target_entity_type": relation.target_entity_type,
        "confidence": _json_safe(relation.confidence),
        "review_status": relation.review_status,
        "rejection_reason": relation.rejection_reason,
        "reviewed_by": relation.reviewed_by,
        "reviewed_at": _json_safe(relation.reviewed_at),
        "source": relation.source,
    }


class AuditLogService:
    def __init__(self, db: Session, repo: AuditLogRepository | None = None) -> None:
        self.db = db
        self.repo = repo or AuditLogRepository(db)

    def log(
        self,
        action: AuditAction,
        *,
        actor: str | None = None,
        target_type: str | None = None,
        target_id: UUID | None = None,
        document_id: UUID | None = None,
        chunk_id: UUID | None = None,
        before: dict[str, Any] | None = None,
        after: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditLog:
        row = AuditLog(
            action=action.value,
            actor=actor,
            target_type=target_type,
            target_id=target_id,
            document_id=document_id,
            chunk_id=chunk_id,
            before_json=json.loads(json.dumps(before, default=_json_safe)) if before else None,
            after_json=json.loads(json.dumps(after, default=_json_safe)) if after else None,
            metadata_json=json.loads(json.dumps(metadata, default=_json_safe)) if metadata else None,
        )
        return self.repo.add(row)
