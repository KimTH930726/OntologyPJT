from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OntologyEntityTypeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    display_name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)


class OntologyEntityTypeUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    is_active: bool | None = None


class OntologyEntityTypeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    display_name: str
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class OntologyRelationTypeCreate(BaseModel):
    source_entity_type: str = Field(min_length=1, max_length=100)
    relation_name: str = Field(min_length=1, max_length=100)
    target_entity_type: str = Field(min_length=1, max_length=100)
    display_name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)


class OntologyRelationTypeUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    is_active: bool | None = None


class OntologyRelationTypeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_entity_type: str
    relation_name: str
    target_entity_type: str
    display_name: str
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
