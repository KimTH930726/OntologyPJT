from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.db.base import Base  # re-export for backward compatibility

__all__ = [
    "Base",
    "get_engine",
    "get_session_factory",
    "ping_postgres",
    "dispose_engine",
]

logger = logging.getLogger(__name__)


_engine: Optional[Engine] = None
_SessionLocal: Optional[sessionmaker] = None


def get_engine() -> Engine:
    global _engine, _SessionLocal
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,
            future=True,
        )
        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False)
    return _engine


def get_session_factory() -> sessionmaker:
    if _SessionLocal is None:
        get_engine()
    assert _SessionLocal is not None
    return _SessionLocal


def ping_postgres() -> tuple[bool, str | None]:
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, None
    except SQLAlchemyError as e:
        logger.warning("postgres ping failed: %s", e)
        return False, str(e.__class__.__name__)
    except Exception as e:  # pragma: no cover
        logger.warning("postgres ping failed: %s", e)
        return False, str(e.__class__.__name__)


def dispose_engine() -> None:
    global _engine
    if _engine is not None:
        _engine.dispose()
        _engine = None
