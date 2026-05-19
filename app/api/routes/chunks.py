from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.repositories.document_chunk_repository import DocumentChunkRepository
from app.schemas.chunk import ChunkOut

router = APIRouter(prefix="/chunks", tags=["chunks"])


@router.get("/{chunk_id}", response_model=ChunkOut)
def get_chunk(chunk_id: UUID, db: Session = Depends(get_db)) -> ChunkOut:
    repo = DocumentChunkRepository(db)
    chunk = repo.get(chunk_id)
    if chunk is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CHUNK_NOT_FOUND"},
        )
    return ChunkOut.model_validate(chunk)
