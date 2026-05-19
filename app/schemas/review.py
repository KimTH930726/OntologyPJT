from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class ReviewApproveRequest(BaseModel):
    reviewer: str = Field(min_length=1, max_length=100)


class ReviewRejectRequest(BaseModel):
    reviewer: str = Field(min_length=1, max_length=100)
    reason: str = Field(min_length=1, max_length=500)


class ReviewModifyEntityRequest(BaseModel):
    reviewer: str = Field(min_length=1, max_length=100)
    name: str | None = Field(default=None, min_length=1, max_length=500)
    normalized_name: str | None = Field(default=None, min_length=1, max_length=200)
    entity_type: str | None = Field(default=None, min_length=1, max_length=100)


class ReviewModifyRelationRequest(BaseModel):
    reviewer: str = Field(min_length=1, max_length=100)
    relation_type: str | None = Field(default=None, min_length=1, max_length=100)
    source_entity_name: str | None = Field(default=None, max_length=200)
    source_entity_type: str | None = Field(default=None, max_length=100)
    target_entity_name: str | None = Field(default=None, max_length=200)
    target_entity_type: str | None = Field(default=None, max_length=100)


class ReviewMergeRequest(BaseModel):
    reviewer: str = Field(min_length=1, max_length=100)
    into_id: UUID
