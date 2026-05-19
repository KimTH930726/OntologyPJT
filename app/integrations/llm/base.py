from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.schemas.extraction import ExtractionResponse


@dataclass(frozen=True)
class EntityTypeSpec:
    name: str
    description: str | None = None


@dataclass(frozen=True)
class RelationTypeSpec:
    source: str
    relation: str
    target: str
    description: str | None = None


@dataclass(frozen=True)
class OntologySnapshot:
    entity_types: tuple[EntityTypeSpec, ...]
    relation_types: tuple[RelationTypeSpec, ...]


class LLMProvider(Protocol):
    """Provider abstraction for entity/relation extraction.

    Implementations MUST return a validated ExtractionResponse. Caller is
    responsible for further ontology validation against the snapshot.
    """

    provider_name: str

    def extract(self, chunk_text: str, snapshot: OntologySnapshot) -> ExtractionResponse: ...
