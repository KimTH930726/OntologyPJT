from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, Template, select_autoescape
from sqlalchemy.orm import Session

from app.repositories.prompt_repository import PromptRepository
from app.services.context_builder import BuiltContext

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
DEFAULT_TEMPLATE_NAME = "qa_default"


@lru_cache
def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(_PROMPTS_DIR)),
        autoescape=select_autoescape(disabled_extensions=("j2",), default=False),
        trim_blocks=True,
        lstrip_blocks=True,
    )


class PromptBuilder:
    def __init__(self, db: Session, repo: PromptRepository | None = None) -> None:
        self.db = db
        self.repo = repo or PromptRepository(db)

    def build_qa(
        self,
        context: BuiltContext,
        question: str,
        *,
        template_name: str = DEFAULT_TEMPLATE_NAME,
    ) -> str:
        tpl = self._load_template(template_name)
        return tpl.render(
            graph_block=context.graph_block,
            evidence_block=context.evidence_block,
            question=question,
        )

    def _load_template(self, name: str) -> Template:
        active = self.repo.get_active_version_by_name(name)
        if active is not None and active.content:
            return _env().from_string(active.content)
        # Fall back to bundled file so QA still works before the seed runs.
        try:
            return _env().get_template(f"{name}.j2")
        except Exception as e:
            logger.warning("template fallback failed (%s): %s", name, e)
            raise
