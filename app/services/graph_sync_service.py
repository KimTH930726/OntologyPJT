"""Sync APPROVED entities/relations from Postgres staging into Neo4j.

Guards:
 1. Only ``review_status == APPROVED`` rows are eligible.
 2. Relation: source/target entity must be APPROVED at sync time (re-checked
    in Postgres) AND must already exist as :Entity nodes in Neo4j.
 3. Relation type must be in the ACTIVE ontology relation whitelist.
 4. Per-row failures are recorded in ``graph_sync_log`` and the loop continues.
 5. By default a SUCCESS history skips re-sync (idempotent + cheap).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.document import Document
from app.db.models.document_chunk import DocumentChunk
from app.db.models.extracted_entity import ExtractedEntity
from app.db.models.extracted_relation import ExtractedRelation
from app.db.models.graph_sync_log import GraphSyncLog
from app.domain.enums import GraphSyncStatus, GraphSyncTargetType, ReviewStatus
from app.repositories.graph_sync_log_repository import GraphSyncLogRepository
from app.repositories.neo4j_repository import Neo4jRepository
from app.repositories.ontology_repository import OntologyRepository

logger = logging.getLogger(__name__)


@dataclass
class GraphSyncSummary:
    entity_success: int = 0
    entity_failed: int = 0
    entity_skipped: int = 0
    relation_success: int = 0
    relation_failed: int = 0
    relation_skipped: int = 0
    errors: list[str] = field(default_factory=list)


class GraphSyncService:
    def __init__(
        self,
        db: Session,
        *,
        neo4j_repo: Neo4jRepository | None = None,
        log_repo: GraphSyncLogRepository | None = None,
        ontology_repo: OntologyRepository | None = None,
    ) -> None:
        self.db = db
        self.neo4j = neo4j_repo or Neo4jRepository()
        self.log_repo = log_repo or GraphSyncLogRepository(db)
        self.ontology = ontology_repo or OntologyRepository(db)

    # ------------------- public -------------------
    def sync_all(self, *, force: bool = False) -> GraphSyncSummary:
        summary = GraphSyncSummary()
        self._sync_entities(force=force, summary=summary)
        # commit entity logs before relations so subsequent relation sync sees them
        self.db.commit()
        self._sync_relations(force=force, summary=summary)
        self.db.commit()
        return summary

    def sync_approved_entities(self, *, force: bool = False) -> GraphSyncSummary:
        summary = GraphSyncSummary()
        self._sync_entities(force=force, summary=summary)
        self.db.commit()
        return summary

    def sync_approved_relations(self, *, force: bool = False) -> GraphSyncSummary:
        summary = GraphSyncSummary()
        self._sync_relations(force=force, summary=summary)
        self.db.commit()
        return summary

    # ------------------- entities -------------------
    def _sync_entities(self, *, force: bool, summary: GraphSyncSummary) -> None:
        rows = self.db.execute(
            select(ExtractedEntity)
            .where(ExtractedEntity.review_status == ReviewStatus.APPROVED.value)
            .where(ExtractedEntity.merged_into_id.is_(None))
            .order_by(ExtractedEntity.created_at.asc())
        ).scalars().all()

        for entity in rows:
            if not force and self.log_repo.has_success(
                GraphSyncTargetType.ENTITY.value, entity.id
            ):
                self._record_log(
                    target_type=GraphSyncTargetType.ENTITY,
                    target_id=entity.id,
                    status=GraphSyncStatus.SKIPPED,
                )
                summary.entity_skipped += 1
                continue
            try:
                self._sync_one_entity(entity)
                summary.entity_success += 1
            except Exception as e:
                logger.exception("entity sync failed: %s", e)
                self._record_log(
                    target_type=GraphSyncTargetType.ENTITY,
                    target_id=entity.id,
                    status=GraphSyncStatus.FAILED,
                    error_message=f"{type(e).__name__}: {e}",
                )
                summary.entity_failed += 1
                summary.errors.append(f"entity {entity.id}: {e}")

    def _sync_one_entity(self, entity: ExtractedEntity) -> None:
        chunk = self.db.get(DocumentChunk, entity.chunk_id)
        if chunk is None:
            raise RuntimeError(f"chunk {entity.chunk_id} not found")
        doc = self.db.get(Document, entity.document_id)
        version = doc.version if doc else "v1"
        confidence = float(entity.confidence) if entity.confidence is not None else None

        neo_id = self.neo4j.merge_entity(
            entity_id=str(entity.id),
            type_=entity.entity_type,
            name=entity.name,
            normalized_name=entity.normalized_name,
            source_document_id=str(entity.document_id),
            chunk_id=str(entity.chunk_id),
            version=version,
            confidence=confidence,
        )
        self.neo4j.merge_document_chunk(
            chunk_id=str(chunk.id),
            document_id=str(entity.document_id),
            text=chunk.text,
            version=version,
        )
        self.neo4j.link_defined_in(entity_id=str(entity.id), chunk_id=str(chunk.id))

        self._record_log(
            target_type=GraphSyncTargetType.ENTITY,
            target_id=entity.id,
            status=GraphSyncStatus.SUCCESS,
            neo4j_node_id=neo_id,
        )

    # ------------------- relations -------------------
    def _sync_relations(self, *, force: bool, summary: GraphSyncSummary) -> None:
        whitelist = {
            rt.relation_name
            for rt in self.ontology.list_relation_types(active_only=True)
        }

        rows = self.db.execute(
            select(ExtractedRelation)
            .where(ExtractedRelation.review_status == ReviewStatus.APPROVED.value)
            .order_by(ExtractedRelation.created_at.asc())
        ).scalars().all()

        for relation in rows:
            if not force and self.log_repo.has_success(
                GraphSyncTargetType.RELATION.value, relation.id
            ):
                self._record_log(
                    target_type=GraphSyncTargetType.RELATION,
                    target_id=relation.id,
                    status=GraphSyncStatus.SKIPPED,
                )
                summary.relation_skipped += 1
                continue
            try:
                self._sync_one_relation(relation, whitelist)
                summary.relation_success += 1
            except Exception as e:
                logger.exception("relation sync failed: %s", e)
                self._record_log(
                    target_type=GraphSyncTargetType.RELATION,
                    target_id=relation.id,
                    status=GraphSyncStatus.FAILED,
                    error_message=f"{type(e).__name__}: {e}",
                )
                summary.relation_failed += 1
                summary.errors.append(f"relation {relation.id}: {e}")

    def _sync_one_relation(
        self, relation: ExtractedRelation, whitelist: set[str]
    ) -> None:
        if relation.relation_type not in whitelist:
            raise RuntimeError(
                f"relation_type '{relation.relation_type}' not in active whitelist"
            )

        src_id = relation.source_entity_id
        tgt_id = relation.target_entity_id
        if src_id is None or tgt_id is None:
            raise RuntimeError("relation has null source/target entity FK")

        src = self.db.get(ExtractedEntity, src_id)
        tgt = self.db.get(ExtractedEntity, tgt_id)
        if src is None or tgt is None:
            raise RuntimeError("source/target staging entity not found")
        if src.review_status != ReviewStatus.APPROVED.value:
            raise RuntimeError("source entity is not APPROVED at sync time")
        if tgt.review_status != ReviewStatus.APPROVED.value:
            raise RuntimeError("target entity is not APPROVED at sync time")
        if not self.log_repo.has_success(
            GraphSyncTargetType.ENTITY.value, src.id
        ) or not self.log_repo.has_success(
            GraphSyncTargetType.ENTITY.value, tgt.id
        ):
            raise RuntimeError("source/target entity not yet synced to Neo4j")

        confidence = (
            float(relation.confidence) if relation.confidence is not None else None
        )
        doc = self.db.get(Document, relation.document_id)
        version = doc.version if doc else "v1"

        # Ensure chunk + defined_in on both endpoints for evidence retrieval.
        chunk = self.db.get(DocumentChunk, relation.chunk_id)
        if chunk is not None:
            self.neo4j.merge_document_chunk(
                chunk_id=str(chunk.id),
                document_id=str(relation.document_id),
                text=chunk.text,
                version=version,
            )
            self.neo4j.link_defined_in(entity_id=str(src.id), chunk_id=str(chunk.id))
            self.neo4j.link_defined_in(entity_id=str(tgt.id), chunk_id=str(chunk.id))

        rel_meta = self.neo4j.merge_relation(
            relation_id=str(relation.id),
            relation_type=relation.relation_type,
            source_entity_id=str(src.id),
            target_entity_id=str(tgt.id),
            confidence=confidence,
            source_document_id=str(relation.document_id),
            chunk_id=str(relation.chunk_id),
            review_id=relation.reviewed_by,
        )
        if rel_meta is None:
            raise RuntimeError("Neo4j MERGE returned no row (endpoints missing?)")

        self._record_log(
            target_type=GraphSyncTargetType.RELATION,
            target_id=relation.id,
            status=GraphSyncStatus.SUCCESS,
            neo4j_relation_id=str(rel_meta.get("id")),
        )

    # ------------------- log helper -------------------
    def _record_log(
        self,
        *,
        target_type: GraphSyncTargetType,
        target_id: UUID,
        status: GraphSyncStatus,
        neo4j_node_id: str | None = None,
        neo4j_relation_id: str | None = None,
        error_message: str | None = None,
    ) -> None:
        row = GraphSyncLog(
            target_type=target_type.value,
            target_id=target_id,
            sync_status=status.value,
            neo4j_node_id=neo4j_node_id,
            neo4j_relation_id=neo4j_relation_id,
            error_message=error_message,
            synced_at=datetime.now(timezone.utc) if status == GraphSyncStatus.SUCCESS else None,
        )
        self.log_repo.add(row)
