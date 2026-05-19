from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.schemas.ontology import (
    OntologyEntityTypeCreate,
    OntologyEntityTypeResponse,
    OntologyEntityTypeUpdate,
    OntologyRelationTypeCreate,
    OntologyRelationTypeResponse,
    OntologyRelationTypeUpdate,
)
from app.services.ontology_schema_service import OntologySchemaService

router = APIRouter(prefix="/ontology", tags=["ontology"])


# =============== entity types ===============
@router.post(
    "/entity-types",
    response_model=OntologyEntityTypeResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_entity_type(
    payload: OntologyEntityTypeCreate, db: Session = Depends(get_db)
) -> OntologyEntityTypeResponse:
    svc = OntologySchemaService(db)
    try:
        row = svc.create_entity_type(payload)
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "DUPLICATE_NAME", "message": str(e.orig)},
        ) from e
    return OntologyEntityTypeResponse.model_validate(row)


@router.get("/entity-types", response_model=list[OntologyEntityTypeResponse])
def list_entity_types(
    active_only: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> list[OntologyEntityTypeResponse]:
    svc = OntologySchemaService(db)
    return [
        OntologyEntityTypeResponse.model_validate(r)
        for r in svc.list_entity_types(active_only=active_only)
    ]


@router.get("/entity-types/{id}", response_model=OntologyEntityTypeResponse)
def get_entity_type(id: UUID, db: Session = Depends(get_db)) -> OntologyEntityTypeResponse:
    svc = OntologySchemaService(db)
    row = svc.repo.get_entity_type(id)
    if row is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND"})
    return OntologyEntityTypeResponse.model_validate(row)


@router.patch("/entity-types/{id}", response_model=OntologyEntityTypeResponse)
def update_entity_type(
    id: UUID, payload: OntologyEntityTypeUpdate, db: Session = Depends(get_db)
) -> OntologyEntityTypeResponse:
    svc = OntologySchemaService(db)
    row = svc.update_entity_type(id, payload)
    if row is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND"})
    db.commit()
    return OntologyEntityTypeResponse.model_validate(row)


@router.delete("/entity-types/{id}", response_model=OntologyEntityTypeResponse)
def deactivate_entity_type(id: UUID, db: Session = Depends(get_db)) -> OntologyEntityTypeResponse:
    svc = OntologySchemaService(db)
    row = svc.deactivate_entity_type(id)
    if row is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND"})
    db.commit()
    return OntologyEntityTypeResponse.model_validate(row)


# =============== relation types ===============
@router.post(
    "/relation-types",
    response_model=OntologyRelationTypeResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_relation_type(
    payload: OntologyRelationTypeCreate, db: Session = Depends(get_db)
) -> OntologyRelationTypeResponse:
    svc = OntologySchemaService(db)
    try:
        row = svc.create_relation_type(payload)
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "DUPLICATE_RELATION", "message": str(e.orig)},
        ) from e
    return OntologyRelationTypeResponse.model_validate(row)


@router.get("/relation-types", response_model=list[OntologyRelationTypeResponse])
def list_relation_types(
    active_only: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> list[OntologyRelationTypeResponse]:
    svc = OntologySchemaService(db)
    return [
        OntologyRelationTypeResponse.model_validate(r)
        for r in svc.list_relation_types(active_only=active_only)
    ]


@router.get("/relation-types/{id}", response_model=OntologyRelationTypeResponse)
def get_relation_type(id: UUID, db: Session = Depends(get_db)) -> OntologyRelationTypeResponse:
    svc = OntologySchemaService(db)
    row = svc.repo.get_relation_type(id)
    if row is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND"})
    return OntologyRelationTypeResponse.model_validate(row)


@router.patch("/relation-types/{id}", response_model=OntologyRelationTypeResponse)
def update_relation_type(
    id: UUID, payload: OntologyRelationTypeUpdate, db: Session = Depends(get_db)
) -> OntologyRelationTypeResponse:
    svc = OntologySchemaService(db)
    row = svc.update_relation_type(id, payload)
    if row is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND"})
    db.commit()
    return OntologyRelationTypeResponse.model_validate(row)


@router.delete("/relation-types/{id}", response_model=OntologyRelationTypeResponse)
def deactivate_relation_type(
    id: UUID, db: Session = Depends(get_db)
) -> OntologyRelationTypeResponse:
    svc = OntologySchemaService(db)
    row = svc.deactivate_relation_type(id)
    if row is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND"})
    db.commit()
    return OntologyRelationTypeResponse.model_validate(row)
