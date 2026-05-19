from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DocumentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    domain: str = Field(min_length=1, max_length=100)
    source_type: str = Field(default="document", max_length=100)
    version: str = Field(default="v1", max_length=50)
    access_level: str = Field(default="internal", max_length=50)
    content: str = Field(min_length=1)


class DocumentCreated(BaseModel):
    document_id: UUID
    chunk_count: int
    vector_status: str  # aggregate: INDEXED / PENDING / FAILED


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    domain: str
    source_type: str
    version: str
    access_level: str
    content_hash: str
    created_at: datetime
    updated_at: datetime


class DocumentDetail(DocumentOut):
    chunk_count: int
    vector_status: str
