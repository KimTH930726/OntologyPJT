from __future__ import annotations

import asyncio
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from app.db.neo4j import ping_neo4j
from app.db.postgres import ping_postgres
from app.db.qdrant import ping_qdrant

router = APIRouter(tags=["health"])

ServiceStatus = Literal["ok", "down"]


class HealthResponse(BaseModel):
    status: ServiceStatus
    services: dict[str, ServiceStatus]
    errors: dict[str, str] = {}


async def _run(fn):
    return await asyncio.to_thread(fn)


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    pg_ok, pg_err = await _run(ping_postgres)
    neo_ok, neo_err = await _run(ping_neo4j)
    qd_ok, qd_err = await _run(ping_qdrant)

    services: dict[str, ServiceStatus] = {
        "postgres": "ok" if pg_ok else "down",
        "neo4j": "ok" if neo_ok else "down",
        "qdrant": "ok" if qd_ok else "down",
    }
    errors = {
        name: err
        for name, err in (("postgres", pg_err), ("neo4j", neo_err), ("qdrant", qd_err))
        if err
    }
    overall: ServiceStatus = "ok" if all(v == "ok" for v in services.values()) else "down"
    return HealthResponse(status=overall, services=services, errors=errors)
