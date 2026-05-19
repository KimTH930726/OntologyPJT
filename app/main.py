from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.db.neo4j import close_neo4j_driver
from app.db.postgres import dispose_engine
from app.db.qdrant import close_qdrant_client

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    setup_logging(settings.log_level)
    logger.info("starting app (env=%s)", settings.app_env)
    try:
        yield
    finally:
        logger.info("shutting down app")
        close_neo4j_driver()
        close_qdrant_client()
        dispose_engine()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Ontology-Grounded RAG Governance Platform",
        version="0.0.1",
        lifespan=lifespan,
    )
    app.include_router(health_router)
    return app


app = create_app()
