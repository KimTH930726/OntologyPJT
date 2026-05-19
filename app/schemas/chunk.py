from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ChunkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    chunk_index: int
    text: str
    token_count: int
    text_hash: str
    vector_status: str
    qdrant_point_id: str | None
    created_at: datetime
    updated_at: datetime
