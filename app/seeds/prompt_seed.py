"""Idempotent prompt template seed: qa_default v1.

Run with::

    docker compose exec app python -m app.seeds.prompt_seed
"""

from __future__ import annotations

import logging
from pathlib import Path

from app.core.logging import setup_logging
from app.db.models.prompt_template import PromptTemplate
from app.db.models.prompt_version import PromptVersion
from app.db.postgres import get_session_factory
from app.repositories.prompt_repository import PromptRepository

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
_QA_TEMPLATE_FILE = _PROMPTS_DIR / "qa_default.j2"


def run() -> None:
    setup_logging("INFO")
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        repo = PromptRepository(db)
        existing_tpl = repo.get_template_by_name("qa_default")
        if existing_tpl is None:
            tpl = PromptTemplate(
                name="qa_default",
                description="Default GraphRAG QA prompt (W4 MVP)",
            )
            repo.add_template(tpl)
            logger.info("created prompt_template: qa_default (id=%s)", tpl.id)
        else:
            tpl = existing_tpl
            logger.info("prompt_template already exists: qa_default (id=%s)", tpl.id)

        if repo.get_active_version(tpl.id) is None:
            content = _QA_TEMPLATE_FILE.read_text(encoding="utf-8")
            version = PromptVersion(
                template_id=tpl.id,
                version=1,
                content=content,
                is_active=True,
            )
            repo.add_version(version)
            logger.info("created prompt_version: qa_default v1 (id=%s)", version.id)
        else:
            logger.info("active prompt_version already present for qa_default")

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    run()
