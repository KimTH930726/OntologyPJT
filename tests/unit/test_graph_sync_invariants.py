"""Regression: GraphSyncService MUST refuse non-APPROVED rows and MUST link
DEFINED_IN for every entity it syncs.

We don't spin up Postgres/Neo4j here. Instead we stub the SQLAlchemy session
and inject fake repositories that record calls. This lets us verify the
control-flow invariants quickly.
"""

from __future__ import annotations

import types
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest

from app.domain.enums import GraphSyncStatus, ReviewStatus
from app.services.graph_sync_service import GraphSyncService


# ---------- fakes ----------
@dataclass
class _Doc:
    version: str = "v1"


@dataclass
class _Chunk:
    id: uuid.UUID
    text: str = "원문"


@dataclass
class _Ent:
    id: uuid.UUID
    document_id: uuid.UUID
    chunk_id: uuid.UUID
    entity_type: str
    name: str
    normalized_name: str
    review_status: str
    confidence: float = 0.9
    merged_into_id: uuid.UUID | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class _Rel:
    id: uuid.UUID
    document_id: uuid.UUID
    chunk_id: uuid.UUID
    source_entity_id: uuid.UUID | None
    target_entity_id: uuid.UUID | None
    relation_type: str
    review_status: str
    confidence: float = 0.9
    reviewed_by: str | None = "alice"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class _FakeNeo4j:
    def __init__(self) -> None:
        self.merged_entities: list[uuid.UUID] = []
        self.merged_relations: list[tuple[uuid.UUID, str]] = []
        self.defined_in: list[tuple[uuid.UUID, uuid.UUID]] = []
        self.chunk_merges: list[uuid.UUID] = []

    def merge_entity(self, *, entity_id: str, **_kw) -> str:
        self.merged_entities.append(uuid.UUID(entity_id))
        return entity_id

    def merge_document_chunk(self, *, chunk_id: str, **_kw) -> None:
        self.chunk_merges.append(uuid.UUID(chunk_id))

    def link_defined_in(self, *, entity_id: str, chunk_id: str) -> None:
        self.defined_in.append((uuid.UUID(entity_id), uuid.UUID(chunk_id)))

    def merge_relation(self, *, relation_id: str, relation_type: str, **_kw) -> dict:
        self.merged_relations.append((uuid.UUID(relation_id), relation_type))
        return {"id": relation_id, "type": relation_type}


class _FakeLogRepo:
    def __init__(self) -> None:
        self.rows: list = []

    def add(self, row):  # noqa: ANN001
        self.rows.append(row)
        return row

    def has_success(self, target_type: str, target_id) -> bool:  # noqa: ANN001
        return any(
            r.target_type == target_type
            and r.target_id == target_id
            and r.sync_status == GraphSyncStatus.SUCCESS.value
            for r in self.rows
        )


class _FakeOntologyRepo:
    def list_relation_types(self, *, active_only: bool = False) -> list:
        # All real seed relation names so REQUIRES/APPLIES_TO pass the whitelist.
        rels = [
            ("Order", "CONTAINS", "OrderItem"),
            ("Order", "PAID_BY", "Payment"),
            ("Refund", "REFUNDS", "Payment"),
            ("Policy", "APPLIES_TO", "Order"),
            ("Policy", "REQUIRES", "Condition"),
            ("Policy", "DEFINED_IN", "DocumentChunk"),
        ]
        return [
            types.SimpleNamespace(
                source_entity_type=s,
                relation_name=r,
                target_entity_type=t,
                is_active=True,
            )
            for s, r, t in rels
        ]


class _FakeSession:
    """Mimics the SQLAlchemy Session surface that GraphSyncService touches."""

    def __init__(
        self,
        entities: list[_Ent],
        relations: list[_Rel],
        chunks: dict[uuid.UUID, _Chunk],
        docs: dict[uuid.UUID, _Doc],
    ) -> None:
        self._entities = entities
        self._relations = relations
        self._chunks = chunks
        self._docs = docs
        self._next_select_returns: list = []
        self.commit_count = 0
        self.flush_count = 0

    def get(self, model, key):  # noqa: ANN001
        from app.db.models.document import Document
        from app.db.models.document_chunk import DocumentChunk
        from app.db.models.extracted_entity import ExtractedEntity

        if model is Document:
            return self._docs.get(key)
        if model is DocumentChunk:
            return self._chunks.get(key)
        if model is ExtractedEntity:
            for e in self._entities:
                if e.id == key:
                    return e
        return None

    def execute(self, stmt):  # noqa: ANN001
        # GraphSyncService runs two SELECTs in order: entities then relations.
        # We can't introspect the statement, so we use a queue.
        if not self._next_select_returns:
            # First call → entities, second call → relations
            self._next_select_returns = [
                _ScalarResult(self._eligible_entities()),
                _ScalarResult(self._eligible_relations()),
            ]
        return self._next_select_returns.pop(0)

    def _eligible_entities(self) -> list[_Ent]:
        return [
            e
            for e in self._entities
            if e.review_status == ReviewStatus.APPROVED.value and e.merged_into_id is None
        ]

    def _eligible_relations(self) -> list[_Rel]:
        return [r for r in self._relations if r.review_status == ReviewStatus.APPROVED.value]

    def commit(self) -> None:
        self.commit_count += 1

    def flush(self) -> None:
        self.flush_count += 1

    def add(self, _row) -> None:  # log inserts (we record in fake log_repo instead)
        pass


class _ScalarResult:
    def __init__(self, rows: list) -> None:
        self._rows = rows

    def scalars(self) -> _ScalarResult:
        return self

    def all(self) -> list:
        return list(self._rows)


# ---------- tests ----------
@pytest.mark.unit
@pytest.mark.invariant
class TestGraphSyncRefusesNonApproved:
    """Invariant 1: only APPROVED entities/relations make it into Neo4j."""

    def _build_service(self) -> tuple[GraphSyncService, _FakeNeo4j, _FakeSession]:
        doc_id = uuid.uuid4()
        chunk_id = uuid.uuid4()
        approved = _Ent(
            id=uuid.uuid4(),
            document_id=doc_id,
            chunk_id=chunk_id,
            entity_type="Policy",
            name="OK",
            normalized_name="OkPolicy",
            review_status=ReviewStatus.APPROVED.value,
        )
        pending = _Ent(
            id=uuid.uuid4(),
            document_id=doc_id,
            chunk_id=chunk_id,
            entity_type="Policy",
            name="Not yet",
            normalized_name="NotYetPolicy",
            review_status=ReviewStatus.PENDING.value,
        )
        rejected = _Ent(
            id=uuid.uuid4(),
            document_id=doc_id,
            chunk_id=chunk_id,
            entity_type="Policy",
            name="Bad",
            normalized_name="BadPolicy",
            review_status=ReviewStatus.REJECTED.value,
        )
        merged = _Ent(
            id=uuid.uuid4(),
            document_id=doc_id,
            chunk_id=chunk_id,
            entity_type="Policy",
            name="Merged",
            normalized_name="Merged",
            review_status=ReviewStatus.APPROVED.value,
            merged_into_id=uuid.uuid4(),
        )
        session = _FakeSession(
            entities=[approved, pending, rejected, merged],
            relations=[],
            chunks={chunk_id: _Chunk(id=chunk_id)},
            docs={doc_id: _Doc()},
        )
        neo = _FakeNeo4j()
        svc = GraphSyncService(
            session,  # type: ignore[arg-type]
            neo4j_repo=neo,  # type: ignore[arg-type]
            log_repo=_FakeLogRepo(),  # type: ignore[arg-type]
            ontology_repo=_FakeOntologyRepo(),  # type: ignore[arg-type]
        )
        return svc, neo, session

    def test_only_approved_non_merged_are_synced(self) -> None:
        svc, neo, _ = self._build_service()
        summary = svc.sync_all()
        assert summary.entity_success == 1
        assert summary.entity_failed == 0
        assert len(neo.merged_entities) == 1


@pytest.mark.unit
@pytest.mark.invariant
class TestGraphSyncLinksDefinedIn:
    """Invariant 4: every entity Neo4j MERGE is accompanied by a DEFINED_IN
    edge to its source chunk."""

    def test_defined_in_called_for_each_entity(self) -> None:
        doc_id = uuid.uuid4()
        chunk_id = uuid.uuid4()
        approved = _Ent(
            id=uuid.uuid4(),
            document_id=doc_id,
            chunk_id=chunk_id,
            entity_type="Policy",
            name="Full",
            normalized_name="FullCancelPolicy",
            review_status=ReviewStatus.APPROVED.value,
        )
        session = _FakeSession(
            entities=[approved],
            relations=[],
            chunks={chunk_id: _Chunk(id=chunk_id)},
            docs={doc_id: _Doc()},
        )
        neo = _FakeNeo4j()
        svc = GraphSyncService(
            session,  # type: ignore[arg-type]
            neo4j_repo=neo,  # type: ignore[arg-type]
            log_repo=_FakeLogRepo(),  # type: ignore[arg-type]
            ontology_repo=_FakeOntologyRepo(),  # type: ignore[arg-type]
        )
        svc.sync_all()
        assert (approved.id, chunk_id) in neo.defined_in


@pytest.mark.unit
@pytest.mark.invariant
class TestGraphSyncRelationRequiresEndpointsSynced:
    """A relation must NOT be synced unless its source AND target entities
    have an ENTITY SUCCESS log entry (i.e. both already in Neo4j)."""

    def test_relation_skipped_when_endpoints_not_synced(self) -> None:
        doc_id = uuid.uuid4()
        chunk_id = uuid.uuid4()
        src = _Ent(
            id=uuid.uuid4(),
            document_id=doc_id,
            chunk_id=chunk_id,
            entity_type="Policy",
            name="P",
            normalized_name="P",
            review_status=ReviewStatus.APPROVED.value,
        )
        # tgt is pending → won't get into ENTITY SUCCESS
        tgt = _Ent(
            id=uuid.uuid4(),
            document_id=doc_id,
            chunk_id=chunk_id,
            entity_type="Condition",
            name="C",
            normalized_name="C",
            review_status=ReviewStatus.PENDING.value,
        )
        rel = _Rel(
            id=uuid.uuid4(),
            document_id=doc_id,
            chunk_id=chunk_id,
            source_entity_id=src.id,
            target_entity_id=tgt.id,
            relation_type="REQUIRES",
            review_status=ReviewStatus.APPROVED.value,
        )
        session = _FakeSession(
            entities=[src, tgt],
            relations=[rel],
            chunks={chunk_id: _Chunk(id=chunk_id)},
            docs={doc_id: _Doc()},
        )
        neo = _FakeNeo4j()
        svc = GraphSyncService(
            session,  # type: ignore[arg-type]
            neo4j_repo=neo,  # type: ignore[arg-type]
            log_repo=_FakeLogRepo(),  # type: ignore[arg-type]
            ontology_repo=_FakeOntologyRepo(),  # type: ignore[arg-type]
        )
        summary = svc.sync_all()
        # src synced; rel must fail because target was not synced (pending).
        assert summary.entity_success == 1
        assert summary.relation_success == 0
        assert summary.relation_failed == 1
        assert neo.merged_relations == []
