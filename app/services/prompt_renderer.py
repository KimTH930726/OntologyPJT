"""Jinja2 prompt rendering for LLM providers.

W2 fake provider does not call this. It exists so the openai/anthropic
providers can render extraction prompts as designed in docs/11.7.1.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.integrations.llm.base import OntologySnapshot

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


@lru_cache
def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(_PROMPTS_DIR)),
        autoescape=select_autoescape(disabled_extensions=("j2",), default=False),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def _ctx(snapshot: OntologySnapshot) -> dict:
    return {
        "entity_types": [
            {"name": e.name, "description": e.description} for e in snapshot.entity_types
        ],
        "relation_types": [
            {
                "source": r.source,
                "relation": r.relation,
                "target": r.target,
                "description": r.description,
            }
            for r in snapshot.relation_types
        ],
    }


def render_extraction_system(snapshot: OntologySnapshot) -> str:
    return _env().get_template("extraction.system.j2").render(**_ctx(snapshot))


def render_extraction_user(chunk_text: str) -> str:
    return _env().get_template("extraction.user.j2").render(chunk_text=chunk_text)


def render_extraction_messages(chunk_text: str, snapshot: OntologySnapshot) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": render_extraction_system(snapshot)},
        {"role": "user", "content": render_extraction_user(chunk_text)},
    ]


def render_extraction_for_anthropic(chunk_text: str, snapshot: OntologySnapshot) -> tuple[str, str]:
    return render_extraction_system(snapshot), render_extraction_user(chunk_text)
