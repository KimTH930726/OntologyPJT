from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.schemas.extraction import ExtractedEntityResponse, ExtractedRelationResponse
from app.schemas.review import (
    ReviewApproveRequest,
    ReviewMergeRequest,
    ReviewModifyEntityRequest,
    ReviewModifyRelationRequest,
    ReviewRejectRequest,
)
from app.services.review_service import (
    NotFoundError,
    ReviewError,
    ReviewService,
    SourceNotApprovedError,
    TargetNotApprovedError,
)

router = APIRouter(prefix="/candidates", tags=["review"])


def _handle(e: Exception) -> None:
    if isinstance(e, NotFoundError):
        raise HTTPException(status_code=404, detail={"code": e.code, "message": str(e)})
    if isinstance(e, (SourceNotApprovedError, TargetNotApprovedError)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": e.code, "message": str(e)},
        )
    if isinstance(e, ReviewError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": e.code, "message": str(e)},
        )
    raise e


# ================ ENTITY ================
@router.post("/entities/{entity_id}/approve", response_model=ExtractedEntityResponse)
def approve_entity(
    entity_id: UUID, payload: ReviewApproveRequest, db: Session = Depends(get_db)
) -> ExtractedEntityResponse:
    svc = ReviewService(db)
    try:
        row = svc.approve_entity(entity_id, payload)
    except ReviewError as e:
        _handle(e)
    return ExtractedEntityResponse.model_validate(row)


@router.post("/entities/{entity_id}/reject", response_model=ExtractedEntityResponse)
def reject_entity(
    entity_id: UUID, payload: ReviewRejectRequest, db: Session = Depends(get_db)
) -> ExtractedEntityResponse:
    svc = ReviewService(db)
    try:
        row = svc.reject_entity(entity_id, payload)
    except ReviewError as e:
        _handle(e)
    return ExtractedEntityResponse.model_validate(row)


@router.patch("/entities/{entity_id}", response_model=ExtractedEntityResponse)
def modify_entity(
    entity_id: UUID,
    payload: ReviewModifyEntityRequest,
    db: Session = Depends(get_db),
) -> ExtractedEntityResponse:
    svc = ReviewService(db)
    try:
        row = svc.modify_entity(entity_id, payload)
    except ReviewError as e:
        _handle(e)
    return ExtractedEntityResponse.model_validate(row)


@router.post("/entities/{entity_id}/merge", response_model=ExtractedEntityResponse)
def merge_entity(
    entity_id: UUID, payload: ReviewMergeRequest, db: Session = Depends(get_db)
) -> ExtractedEntityResponse:
    svc = ReviewService(db)
    try:
        row = svc.merge_entity(entity_id, payload)
    except ReviewError as e:
        _handle(e)
    return ExtractedEntityResponse.model_validate(row)


# ================ RELATION ================
@router.post("/relations/{relation_id}/approve", response_model=ExtractedRelationResponse)
def approve_relation(
    relation_id: UUID, payload: ReviewApproveRequest, db: Session = Depends(get_db)
) -> ExtractedRelationResponse:
    svc = ReviewService(db)
    try:
        row = svc.approve_relation(relation_id, payload)
    except ReviewError as e:
        _handle(e)
    return ExtractedRelationResponse.model_validate(row)


@router.post("/relations/{relation_id}/reject", response_model=ExtractedRelationResponse)
def reject_relation(
    relation_id: UUID, payload: ReviewRejectRequest, db: Session = Depends(get_db)
) -> ExtractedRelationResponse:
    svc = ReviewService(db)
    try:
        row = svc.reject_relation(relation_id, payload)
    except ReviewError as e:
        _handle(e)
    return ExtractedRelationResponse.model_validate(row)


@router.patch("/relations/{relation_id}", response_model=ExtractedRelationResponse)
def modify_relation(
    relation_id: UUID,
    payload: ReviewModifyRelationRequest,
    db: Session = Depends(get_db),
) -> ExtractedRelationResponse:
    svc = ReviewService(db)
    try:
        row = svc.modify_relation(relation_id, payload)
    except ReviewError as e:
        _handle(e)
    return ExtractedRelationResponse.model_validate(row)


@router.post("/relations/{relation_id}/merge", response_model=ExtractedRelationResponse)
def merge_relation(
    relation_id: UUID, payload: ReviewMergeRequest, db: Session = Depends(get_db)
) -> ExtractedRelationResponse:
    svc = ReviewService(db)
    try:
        row = svc.merge_relation(relation_id, payload)
    except ReviewError as e:
        _handle(e)
    return ExtractedRelationResponse.model_validate(row)
