from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LLMEntityCandidate(BaseModel):
    """Schema for a single entity emitted by an LLM provider."""

    name: str
    type: str
    normalized_name: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_text: str
    needs_review: bool = False


class LLMRelationCandidate(BaseModel):
    """Schema for a single relation emitted by an LLM provider."""

    source: str
    source_type: str
    relation: str
    target: str
    target_type: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_text: str
    needs_review: bool = False


class ExtractionResponse(BaseModel):
    """Full LLM response: a list of entities and relations."""

    entities: list[LLMEntityCandidate] = Field(default_factory=list)
    relations: list[LLMRelationCandidate] = Field(default_factory=list)


class ExtractionRunResponse(BaseModel):
    """API response for POST /extract endpoints."""

    document_id: UUID
    chunk_ids: list[UUID]
    entities_extracted: int
    relations_extracted: int
    schema_violations: int
    audit_log_id: UUID | None


class ExtractedEntityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    chunk_id: UUID
    entity_type: str
    name: str
    normalized_name: str
    confidence: Decimal
    evidence_text: str | None
    source: str
    review_status: str
    reviewed_by: str | None
    reviewed_at: datetime | None
    rejection_reason: str | None
    merged_into_id: UUID | None
    created_at: datetime
    updated_at: datetime


class ExtractedRelationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    chunk_id: UUID
    source_entity_id: UUID | None
    source_entity_name: str
    source_entity_type: str
    relation_type: str
    target_entity_id: UUID | None
    target_entity_name: str
    target_entity_type: str
    confidence: Decimal
    evidence_text: str | None
    source: str
    review_status: str
    reviewed_by: str | None
    reviewed_at: datetime | None
    rejection_reason: str | None
    created_at: datetime
    updated_at: datetime


class DocumentCandidatesResponse(BaseModel):
    entities: list[ExtractedEntityResponse]
    relations: list[ExtractedRelationResponse]
