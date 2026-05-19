from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

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


def _resolve_admin_dir() -> Path:
    # Override path (used by Docker image so the SPA survives a host-volume
    # mount over /code/app). Default: app/static/admin.
    override = os.environ.get("ADMIN_STATIC_DIR")
    if override:
        return Path(override).resolve()
    return Path(__file__).resolve().parent / "static" / "admin"


ADMIN_STATIC_DIR = _resolve_admin_dir()


def _mount_admin(app: FastAPI) -> None:
    """Serve the built React admin SPA at /admin (if present).

    Hashed assets live under /admin/assets/*; everything else under /admin/*
    falls back to index.html so client-side routes (e.g. /admin/candidates)
    resolve correctly on hard refresh.
    """
    if not ADMIN_STATIC_DIR.is_dir() or not (ADMIN_STATIC_DIR / "index.html").is_file():
        logger.info("admin SPA bundle not found at %s; skipping mount", ADMIN_STATIC_DIR)
        return

    assets_dir = ADMIN_STATIC_DIR / "assets"
    if assets_dir.is_dir():
        app.mount(
            "/admin/assets",
            StaticFiles(directory=str(assets_dir)),
            name="admin-assets",
        )

    index_path = ADMIN_STATIC_DIR / "index.html"

    @app.get("/admin", include_in_schema=False)
    @app.get("/admin/", include_in_schema=False)
    @app.get("/admin/{full_path:path}", include_in_schema=False)
    def admin_spa(full_path: str = "") -> FileResponse:
        # Serve a top-level static file (e.g. /admin/vite.svg) directly if it
        # exists; otherwise hand the request to the SPA shell.
        if full_path:
            candidate = ADMIN_STATIC_DIR / full_path
            if candidate.is_file() and candidate.resolve().is_relative_to(
                ADMIN_STATIC_DIR.resolve()
            ):
                return FileResponse(candidate)
        return FileResponse(index_path)

    logger.info("admin SPA mounted at /admin (from %s)", ADMIN_STATIC_DIR)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Ontology-Grounded RAG Governance Platform",
        version="0.0.1",
        lifespan=lifespan,
    )
    # CORS — admin SPA dev server (vite) runs on :5173 and calls the API directly.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
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

    @app.get("/", include_in_schema=False)
    def root() -> RedirectResponse:
        target = "/admin/" if (ADMIN_STATIC_DIR / "index.html").is_file() else "/docs"
        return RedirectResponse(url=target)

    _mount_admin(app)

    return app


app = create_app()
