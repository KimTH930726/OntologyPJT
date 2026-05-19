from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class GraphSyncResult(BaseModel):
    entity_success: int = 0
    entity_failed: int = 0
    entity_skipped: int = 0
    relation_success: int = 0
    relation_failed: int = 0
    relation_skipped: int = 0

    @property
    def total_success(self) -> int:
        return self.entity_success + self.relation_success

    @property
    def total_failed(self) -> int:
        return self.entity_failed + self.relation_failed

    @property
    def skipped(self) -> int:
        return self.entity_skipped + self.relation_skipped


class GraphSyncLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    target_type: str
    target_id: UUID
    sync_status: str
    neo4j_node_id: str | None
    neo4j_relation_id: str | None
    error_message: str | None
    synced_at: datetime | None
    created_at: datetime


class DefinedInChunk(BaseModel):
    chunk_id: UUID
    document_id: UUID | None
    text: str | None


class GraphEntityResponse(BaseModel):
    id: UUID
    type: str
    name: str
    normalized_name: str
    source_document_id: UUID | None
    chunk_id: UUID | None
    confidence: Decimal | float | None
    defined_in: list[DefinedInChunk]


class GraphNode(BaseModel):
    id: UUID
    type: str
    normalized_name: str
    name: str | None = None


class GraphRelationship(BaseModel):
    id: UUID | None
    source: str
    target: str
    relation: str
    confidence: float | None = None
    chunk_id: UUID | None = None


class SubgraphResponse(BaseModel):
    seed: str
    depth: int
    nodes: list[GraphNode]
    relationships: list[GraphRelationship]
