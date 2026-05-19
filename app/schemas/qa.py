from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class QARequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)


class GraphContextSummary(BaseModel):
    seed_entities: list[str] = []
    triple_count: int = 0


class DocumentEvidenceSummary(BaseModel):
    chunk_count: int = 0


class QAResponse(BaseModel):
    answer: str
    graph_context: GraphContextSummary
    document_evidence: DocumentEvidenceSummary
    query_log_id: UUID


class AIQueryLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    question: str
    detected_entities_json: Any | None
    graph_context_json: Any | None
    retrieved_chunks_json: Any | None
    final_prompt: str
    answer: str | None
    model_provider: str | None
    model_name: str | None
    token_estimate: int | None
    latency_ms: int | None
    error_message: str | None
    created_at: datetime
