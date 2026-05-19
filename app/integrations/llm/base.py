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
    """Provider abstraction for both extraction (W2) and QA (W4).

    ``provider_name`` is used to tag audit/log rows.
    ``model_name`` is reported alongside (``"fake"`` for the deterministic
    provider). ``extract`` is used at ingest time, ``answer`` and
    ``extract_intent_entities`` at query time.
    """

    provider_name: str
    model_name: str

    def extract(self, chunk_text: str, snapshot: OntologySnapshot) -> ExtractionResponse: ...

    def answer(self, prompt: str) -> str: ...

    def extract_intent_entities(self, question: str) -> list[str]: ...
