from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy.orm import Session

from app.db.postgres import get_session_factory


def get_db() -> Iterator[Session]:
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
