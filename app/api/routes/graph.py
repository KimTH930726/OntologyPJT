from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.repositories.graph_sync_log_repository import GraphSyncLogRepository
from app.repositories.neo4j_repository import Neo4jRepository
from app.repositories.ontology_repository import OntologyRepository
from app.schemas.graph import (
    DefinedInChunk,
    GraphEntityResponse,
    GraphNode,
    GraphRelationship,
    GraphSyncLogResponse,
    GraphSyncResult,
    SubgraphResponse,
)
from app.services.graph_sync_service import GraphSyncService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/graph", tags=["graph"])


# ============== sync endpoints ==============
@router.post("/sync", response_model=GraphSyncResult)
def sync_all(force: bool = Query(default=False), db: Session = Depends(get_db)) -> GraphSyncResult:
    svc = GraphSyncService(db)
    s = svc.sync_all(force=force)
    return GraphSyncResult(
        entity_success=s.entity_success,
        entity_failed=s.entity_failed,
        entity_skipped=s.entity_skipped,
        relation_success=s.relation_success,
        relation_failed=s.relation_failed,
        relation_skipped=s.relation_skipped,
    )


@router.post("/sync/entities", response_model=GraphSyncResult)
def sync_entities(force: bool = Query(default=False), db: Session = Depends(get_db)) -> GraphSyncResult:
    svc = GraphSyncService(db)
    s = svc.sync_approved_entities(force=force)
    return GraphSyncResult(
        entity_success=s.entity_success,
        entity_failed=s.entity_failed,
        entity_skipped=s.entity_skipped,
    )


@router.post("/sync/relations", response_model=GraphSyncResult)
def sync_relations(force: bool = Query(default=False), db: Session = Depends(get_db)) -> GraphSyncResult:
    svc = GraphSyncService(db)
    s = svc.sync_approved_relations(force=force)
    return GraphSyncResult(
        relation_success=s.relation_success,
        relation_failed=s.relation_failed,
        relation_skipped=s.relation_skipped,
    )


@router.get("/sync-logs", response_model=list[GraphSyncLogResponse])
def list_sync_logs(
    target_type: str | None = Query(default=None),
    target_id: UUID | None = Query(default=None),
    sync_status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[GraphSyncLogResponse]:
    repo = GraphSyncLogRepository(db)
    rows = repo.list(
        target_type=target_type,
        target_id=target_id,
        sync_status=sync_status,
        limit=limit,
        offset=offset,
    )
    return [GraphSyncLogResponse.model_validate(r) for r in rows]


# ============== graph query endpoints ==============
def _ensure_safe_seed(name: str) -> str:
    n = name.strip()
    if not n or len(n) > 200:
        raise HTTPException(status_code=400, detail={"code": "INVALID_SEED"})
    return n


@router.get("/entities/{normalized_name}", response_model=GraphEntityResponse)
def get_entity(normalized_name: str) -> GraphEntityResponse:
    name = _ensure_safe_seed(normalized_name)
    repo = Neo4jRepository()
    try:
        view = repo.fetch_entity_view(name)
    except Exception as e:
        logger.exception("graph entity fetch failed")
        raise HTTPException(status_code=502, detail={"code": "NEO4J_ERROR", "message": str(e)}) from e
    if view is None:
        raise HTTPException(status_code=404, detail={"code": "ENTITY_NOT_FOUND"})
    return GraphEntityResponse(
        id=view["id"],
        type=view["type"],
        name=view["name"],
        normalized_name=view["normalized_name"],
        source_document_id=view.get("source_document_id"),
        chunk_id=view.get("chunk_id"),
        confidence=view.get("confidence"),
        defined_in=[
            DefinedInChunk(
                chunk_id=d["chunk_id"],
                document_id=d.get("document_id"),
                text=d.get("text"),
            )
            for d in view["defined_in"]
        ],
    )


@router.get("/subgraph", response_model=SubgraphResponse)
def get_subgraph(
    seed: str = Query(..., min_length=1, max_length=200),
    depth: int = Query(default=2, ge=0, le=5),
    db: Session = Depends(get_db),
) -> SubgraphResponse:
    name = _ensure_safe_seed(seed)
    ontology = OntologyRepository(db)
    whitelist = [rt.relation_name for rt in ontology.list_relation_types(active_only=True)]
    rel_filter = "|".join(sorted(set(whitelist))) if whitelist else None

    repo = Neo4jRepository()
    try:
        sub = repo.fetch_subgraph(name, depth, rel_filter)
    except Exception as e:
        logger.exception("subgraph fetch failed")
        raise HTTPException(status_code=502, detail={"code": "NEO4J_ERROR", "message": str(e)}) from e

    if not sub["nodes"]:
        raise HTTPException(status_code=404, detail={"code": "SEED_NOT_FOUND"})

    return SubgraphResponse(
        seed=name,
        depth=depth,
        nodes=[GraphNode(**n) for n in sub["nodes"]],
        relationships=[GraphRelationship(**r) for r in sub["relationships"]],
    )
