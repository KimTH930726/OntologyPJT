from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.schemas.chunk import ChunkOut
from app.schemas.document import (
    DocumentCreate,
    DocumentCreated,
    DocumentDetail,
    DocumentOut,
)
from app.services.document_service import DocumentService, DuplicateDocumentError

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=DocumentCreated, status_code=status.HTTP_201_CREATED)
def create_document(payload: DocumentCreate, db: Session = Depends(get_db)) -> DocumentCreated:
    service = DocumentService(db)
    try:
        result = service.create_document(
            title=payload.title,
            domain=payload.domain,
            source_type=payload.source_type,
            version=payload.version,
            access_level=payload.access_level,
            content=payload.content,
        )
    except DuplicateDocumentError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "DUPLICATE_CONTENT",
                "message": "document with same content already exists",
                "existing_document_id": str(e.existing_id),
            },
        ) from e

    return DocumentCreated(
        document_id=result.document.id,
        chunk_count=result.chunk_count,
        vector_status=result.aggregate_status.value,
    )


@router.get("", response_model=list[DocumentOut])
def list_documents(
    domain: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[DocumentOut]:
    service = DocumentService(db)
    items, _ = service.list_documents(domain=domain, limit=limit, offset=offset)
    return [DocumentOut.model_validate(d) for d in items]


@router.get("/{document_id}", response_model=DocumentDetail)
def get_document(document_id: UUID, db: Session = Depends(get_db)) -> DocumentDetail:
    service = DocumentService(db)
    doc = service.get(document_id)
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "DOCUMENT_NOT_FOUND"},
        )
    count, agg = service.aggregate_status(document_id)
    base = DocumentOut.model_validate(doc).model_dump()
    return DocumentDetail(**base, chunk_count=count, vector_status=agg.value)


@router.get("/{document_id}/chunks", response_model=list[ChunkOut])
def list_document_chunks(document_id: UUID, db: Session = Depends(get_db)) -> list[ChunkOut]:
    service = DocumentService(db)
    if service.get(document_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "DOCUMENT_NOT_FOUND"},
        )
    return [ChunkOut.model_validate(c) for c in service.list_chunks(document_id)]
