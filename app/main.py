from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.audit import router as audit_router
from app.api.routes.chunks import router as chunks_router
from app.api.routes.documents import router as documents_router
from app.api.routes.extraction import router as extraction_router
from app.api.routes.graph import router as graph_router
from app.api.routes.health import router as health_router
from app.api.routes.ontology import router as ontology_router
from app.api.routes.qa import router as qa_router
from app.api.routes.review import router as review_router
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.db.neo4j import close_neo4j_driver
from app.db.postgres import dispose_engine
from app.db.qdrant import close_qdrant_client
from app.repositories.neo4j_repository import Neo4jRepository

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    setup_logging(settings.log_level)
    logger.info("starting app (env=%s)", settings.app_env)
    try:
        Neo4jRepository().ensure_schema()
        logger.info("neo4j schema ensured")
    except Exception as e:
        logger.warning("neo4j schema ensure skipped: %s", e)
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
    app.include_router(documents_router)
    app.include_router(chunks_router)
    app.include_router(ontology_router)
    app.include_router(extraction_router)
    app.include_router(review_router)
    app.include_router(graph_router)
    app.include_router(qa_router)
    app.include_router(audit_router)
    return app


app = create_app()
