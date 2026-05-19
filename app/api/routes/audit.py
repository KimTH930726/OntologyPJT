from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.repositories.audit_log_repository import AuditLogRepository
from app.schemas.audit import AuditLogResponse

router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.get("", response_model=list[AuditLogResponse])
def list_audit_logs(
    action: str | None = Query(default=None),
    target_type: str | None = Query(default=None),
    target_id: UUID | None = Query(default=None),
    document_id: UUID | None = Query(default=None),
    chunk_id: UUID | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[AuditLogResponse]:
    repo = AuditLogRepository(db)
    rows = repo.list(
        action=action,
        target_type=target_type,
        target_id=target_id,
        document_id=document_id,
        chunk_id=chunk_id,
        limit=limit,
        offset=offset,
    )
    return [AuditLogResponse.model_validate(r) for r in rows]


@router.get("/{id}", response_model=AuditLogResponse)
def get_audit_log(id: UUID, db: Session = Depends(get_db)) -> AuditLogResponse:
    repo = AuditLogRepository(db)
    row = repo.get(id)
    if row is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND"})
    return AuditLogResponse.model_validate(row)
