from __future__ import annotations

import logging

from neo4j import Driver, GraphDatabase

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_driver: Driver | None = None


def get_neo4j_driver() -> Driver:
    global _driver
    if _driver is None:
        s = get_settings()
        _driver = GraphDatabase.driver(
            s.neo4j_uri,
            auth=(s.neo4j_user, s.neo4j_password),
        )
    return _driver


def ping_neo4j() -> tuple[bool, str | None]:
    try:
        driver = get_neo4j_driver()
        with driver.session() as session:
            result = session.run("RETURN 1 AS ok")
            ok = result.single()
            return (ok is not None and ok["ok"] == 1), None
    except Exception as e:
        logger.warning("neo4j ping failed: %s", e)
        return False, str(e.__class__.__name__)


def close_neo4j_driver() -> None:
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None
