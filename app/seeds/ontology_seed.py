"""Idempotent ontology seed for the e-commerce policy domain.

Run with::

    docker compose exec app python -m app.seeds.ontology_seed
"""
from __future__ import annotations

import logging

from app.core.logging import setup_logging
from app.db.postgres import get_session_factory
from app.schemas.ontology import (
    OntologyEntityTypeCreate,
    OntologyRelationTypeCreate,
)
from app.services.ontology_schema_service import OntologySchemaService

logger = logging.getLogger(__name__)


ENTITY_TYPES: list[OntologyEntityTypeCreate] = [
    OntologyEntityTypeCreate(name="Order", display_name="주문"),
    OntologyEntityTypeCreate(name="OrderItem", display_name="주문 상품"),
    OntologyEntityTypeCreate(name="Product", display_name="상품"),
    OntologyEntityTypeCreate(name="Payment", display_name="결제"),
    OntologyEntityTypeCreate(name="Refund", display_name="환불"),
    OntologyEntityTypeCreate(name="Delivery", display_name="배송"),
    OntologyEntityTypeCreate(name="Policy", display_name="정책"),
    OntologyEntityTypeCreate(name="Condition", display_name="조건"),
    OntologyEntityTypeCreate(name="DocumentChunk", display_name="문서 청크"),
]


RELATION_TYPES: list[OntologyRelationTypeCreate] = [
    OntologyRelationTypeCreate(
        source_entity_type="Order",
        relation_name="CONTAINS",
        target_entity_type="OrderItem",
        display_name="Order CONTAINS OrderItem",
    ),
    OntologyRelationTypeCreate(
        source_entity_type="Order",
        relation_name="PAID_BY",
        target_entity_type="Payment",
        display_name="Order PAID_BY Payment",
    ),
    OntologyRelationTypeCreate(
        source_entity_type="Refund",
        relation_name="REFUNDS",
        target_entity_type="Payment",
        display_name="Refund REFUNDS Payment",
    ),
    OntologyRelationTypeCreate(
        source_entity_type="Policy",
        relation_name="APPLIES_TO",
        target_entity_type="Order",
        display_name="Policy APPLIES_TO Order",
    ),
    OntologyRelationTypeCreate(
        source_entity_type="Policy",
        relation_name="REQUIRES",
        target_entity_type="Condition",
        display_name="Policy REQUIRES Condition",
    ),
    OntologyRelationTypeCreate(
        source_entity_type="Policy",
        relation_name="DEFINED_IN",
        target_entity_type="DocumentChunk",
        display_name="Policy DEFINED_IN DocumentChunk",
    ),
]


def run() -> None:
    setup_logging("INFO")
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        svc = OntologySchemaService(db)
        for et in ENTITY_TYPES:
            row = svc.create_entity_type(et)
            logger.info("entity_type: %s (id=%s)", row.name, row.id)
        for rt in RELATION_TYPES:
            row = svc.create_relation_type(rt)
            logger.info(
                "relation_type: %s %s %s (id=%s)",
                row.source_entity_type, row.relation_name, row.target_entity_type, row.id,
            )
        db.commit()
        logger.info(
            "seed complete: %d entity types, %d relation types",
            len(ENTITY_TYPES), len(RELATION_TYPES),
        )
    finally:
        db.close()


if __name__ == "__main__":
    run()
