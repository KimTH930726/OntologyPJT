from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.repositories.extraction_repository import ExtractionRepository
from app.schemas.extraction import (
    DocumentCandidatesResponse,
    ExtractedEntityResponse,
    ExtractedRelationResponse,
    ExtractionRunResponse,
)
from app.services.entity_relation_extraction_service import (
    EntityRelationExtractionService,
)

router = APIRouter(tags=["extraction"])


@router.post(
    "/documents/{document_id}/extract",
    response_model=ExtractionRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def extract_document(document_id: UUID, db: Session = Depends(get_db)) -> ExtractionRunResponse:
    svc = EntityRelationExtractionService(db)
    try:
        result = svc.extract_document(document_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail={"code": "DOCUMENT_NOT_FOUND"}) from e
    return ExtractionRunResponse(**result.__dict__)


@router.post(
    "/chunks/{chunk_id}/extract",
    response_model=ExtractionRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def extract_chunk(chunk_id: UUID, db: Session = Depends(get_db)) -> ExtractionRunResponse:
    svc = EntityRelationExtractionService(db)
    try:
        result = svc.extract_chunk(chunk_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail={"code": "CHUNK_NOT_FOUND"}) from e
    return ExtractionRunResponse(**result.__dict__)


@router.get("/candidates/entities", response_model=list[ExtractedEntityResponse])
def list_entity_candidates(
    document_id: UUID | None = Query(default=None),
    chunk_id: UUID | None = Query(default=None),
    review_status: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[ExtractedEntityResponse]:
    repo = ExtractionRepository(db)
    rows = repo.list_entities(
        document_id=document_id,
        chunk_id=chunk_id,
        review_status=review_status,
        entity_type=entity_type,
        limit=limit,
        offset=offset,
    )
    return [ExtractedEntityResponse.model_validate(r) for r in rows]


@router.get("/candidates/relations", response_model=list[ExtractedRelationResponse])
def list_relation_candidates(
    document_id: UUID | None = Query(default=None),
    chunk_id: UUID | None = Query(default=None),
    review_status: str | None = Query(default=None),
    relation_type: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[ExtractedRelationResponse]:
    repo = ExtractionRepository(db)
    rows = repo.list_relations(
        document_id=document_id,
        chunk_id=chunk_id,
        review_status=review_status,
        relation_type=relation_type,
        limit=limit,
        offset=offset,
    )
    return [ExtractedRelationResponse.model_validate(r) for r in rows]


@router.get(
    "/documents/{document_id}/candidates", response_model=DocumentCandidatesResponse
)
def list_document_candidates(
    document_id: UUID,
    review_status: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> DocumentCandidatesResponse:
    repo = ExtractionRepository(db)
    entities = repo.list_entities(document_id=document_id, review_status=review_status, limit=500)
    relations = repo.list_relations(document_id=document_id, review_status=review_status, limit=500)
    return DocumentCandidatesResponse(
        entities=[ExtractedEntityResponse.model_validate(e) for e in entities],
        relations=[ExtractedRelationResponse.model_validate(r) for r in relations],
    )
