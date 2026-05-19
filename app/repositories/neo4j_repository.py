"""Cypher access for the approved ontology graph.

Public API is intentionally narrow — only GraphSyncService is allowed to
write to Neo4j. Read methods are used by Graph API and (in W4) GraphRetriever.

Relationship types are NEVER taken from raw user input. The caller MUST pass
a relation_type that has already been validated against the active relation
type whitelist; this class re-checks against an allow-list pattern as defense
in depth before string-interpolating it into Cypher.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from neo4j import Driver

from app.db.neo4j import get_neo4j_driver

logger = logging.getLogger(__name__)

# Defense in depth. Both regexes reject anything Cypher could interpret as
# something other than a plain identifier (no whitespace, no backticks, no
# semicolons, length-bounded).
_REL_NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
_LABEL_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,63}$")


SCHEMA_STATEMENTS: tuple[str, ...] = (
    "CREATE CONSTRAINT entity_id_unique IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE",
    "CREATE INDEX entity_normalized_name_index IF NOT EXISTS FOR (e:Entity) ON (e.normalized_name)",
    "CREATE INDEX entity_type_index IF NOT EXISTS FOR (e:Entity) ON (e.type)",
    "CREATE CONSTRAINT chunk_id_unique IF NOT EXISTS "
    "FOR (c:DocumentChunk) REQUIRE c.chunk_id IS UNIQUE",
)


def assert_safe_relation_type(rel_type: str) -> None:
    if not _REL_NAME_RE.match(rel_type):
        raise ValueError(f"unsafe relation type: {rel_type!r}")


def assert_safe_label(label: str) -> None:
    if not _LABEL_RE.match(label):
        raise ValueError(f"unsafe label: {label!r}")


class Neo4jRepository:
    def __init__(self, driver: Driver | None = None) -> None:
        self.driver = driver or get_neo4j_driver()

    # ---------------- schema ----------------
    def ensure_schema(self) -> None:
        with self.driver.session() as sess:
            for stmt in SCHEMA_STATEMENTS:
                sess.run(stmt)

    # ---------------- writes ----------------
    def merge_entity(
        self,
        *,
        entity_id: str,
        type_: str,
        name: str,
        normalized_name: str,
        source_document_id: str,
        chunk_id: str,
        version: str,
        confidence: float | None,
    ) -> str:
        """MERGE an Entity by id and (re-)set its properties.

        Also attaches a dynamic label matching ``type_`` so domain queries
        like ``MATCH (p:Policy)`` work.
        """
        assert_safe_label(type_)  # type doubles as a Neo4j label
        cypher = (
            "MERGE (e:Entity {id: $id}) "
            "SET e.type = $type, e.name = $name, "
            "    e.normalized_name = $normalized_name, "
            "    e.source_document_id = $source_document_id, "
            "    e.chunk_id = $chunk_id, e.version = $version, "
            "    e.confidence = $confidence, "
            "    e.created_at = coalesce(e.created_at, datetime()), "
            "    e.updated_at = datetime() "
            f"WITH e CALL apoc.create.addLabels(e, ['{type_}']) "
            "YIELD node RETURN node.id AS id"
        )
        with self.driver.session() as sess:
            result = sess.run(
                cypher,
                id=entity_id,
                type=type_,
                name=name,
                normalized_name=normalized_name,
                source_document_id=source_document_id,
                chunk_id=chunk_id,
                version=version,
                confidence=confidence,
            )
            row = result.single()
            return row["id"] if row else entity_id

    def merge_document_chunk(
        self,
        *,
        chunk_id: str,
        document_id: str,
        text: str | None,
        version: str,
    ) -> None:
        cypher = (
            "MERGE (c:DocumentChunk {chunk_id: $chunk_id}) "
            "SET c.document_id = $document_id, c.text = $text, "
            "    c.version = $version, "
            "    c.created_at = coalesce(c.created_at, datetime()), "
            "    c.updated_at = datetime()"
        )
        with self.driver.session() as sess:
            sess.run(
                cypher,
                chunk_id=chunk_id,
                document_id=document_id,
                text=text,
                version=version,
            )

    def link_defined_in(self, *, entity_id: str, chunk_id: str) -> None:
        cypher = (
            "MATCH (e:Entity {id: $entity_id}) "
            "MATCH (c:DocumentChunk {chunk_id: $chunk_id}) "
            "MERGE (e)-[r:DEFINED_IN]->(c) "
            "  ON CREATE SET r.created_at = datetime()"
        )
        with self.driver.session() as sess:
            sess.run(cypher, entity_id=entity_id, chunk_id=chunk_id)

    def merge_relation(
        self,
        *,
        relation_id: str,
        relation_type: str,
        source_entity_id: str,
        target_entity_id: str,
        confidence: float | None,
        source_document_id: str,
        chunk_id: str,
        review_id: str | None,
    ) -> dict[str, Any] | None:
        """MERGE a typed relationship between two Entity nodes.

        Caller must pass a whitelisted ``relation_type``. We re-validate it
        against a strict regex before string-interpolating into Cypher.
        """
        assert_safe_relation_type(relation_type)
        # Both endpoints must already exist; otherwise return None to caller
        # so it can record FAILED in graph_sync_log.
        cypher = (
            "MATCH (s:Entity {id: $source_id}) "
            "MATCH (t:Entity {id: $target_id}) "
            f"MERGE (s)-[r:`{relation_type}` {{id: $relation_id}}]->(t) "
            "ON CREATE SET r.created_at = datetime() "
            "SET r.relation_type = $relation_type, r.confidence = $confidence, "
            "    r.source_document_id = $source_document_id, "
            "    r.chunk_id = $chunk_id, r.review_id = $review_id, "
            "    r.updated_at = datetime() "
            "RETURN r.id AS id, type(r) AS type"
        )
        with self.driver.session() as sess:
            result = sess.run(
                cypher,
                source_id=source_entity_id,
                target_id=target_entity_id,
                relation_id=relation_id,
                relation_type=relation_type,
                confidence=confidence,
                source_document_id=source_document_id,
                chunk_id=chunk_id,
                review_id=review_id,
            )
            row = result.single()
            return {"id": row["id"], "type": row["type"]} if row else None

    # ---------------- reads ----------------
    def list_normalized_names(self) -> list[str]:
        cypher = "MATCH (e:Entity) RETURN DISTINCT e.normalized_name AS name"
        with self.driver.session() as sess:
            return [row["name"] for row in sess.run(cypher) if row["name"]]

    def fetch_entity_view(self, normalized_name: str) -> dict[str, Any] | None:
        cypher = (
            "MATCH (e:Entity {normalized_name: $name}) "
            "OPTIONAL MATCH (e)-[:DEFINED_IN]->(c:DocumentChunk) "
            "WITH e, collect(DISTINCT { "
            "  chunk_id: c.chunk_id, document_id: c.document_id, text: c.text "
            "}) AS defined_in "
            "RETURN e.id AS id, e.type AS type, e.name AS name, "
            "       e.normalized_name AS normalized_name, "
            "       e.source_document_id AS source_document_id, "
            "       e.chunk_id AS chunk_id, e.confidence AS confidence, "
            "       defined_in "
            "ORDER BY e.created_at DESC LIMIT 1"
        )
        with self.driver.session() as sess:
            row = sess.run(cypher, name=normalized_name).single()
            if row is None:
                return None
            return {
                "id": row["id"],
                "type": row["type"],
                "name": row["name"],
                "normalized_name": row["normalized_name"],
                "source_document_id": row["source_document_id"],
                "chunk_id": row["chunk_id"],
                "confidence": row["confidence"],
                "defined_in": [d for d in row["defined_in"] if d.get("chunk_id") is not None],
            }

    def fetch_subgraph(
        self,
        normalized_name: str,
        depth: int,
        relationship_filter: str | None = None,
    ) -> dict[str, Any]:
        """APOC-backed subgraph from a normalized_name seed.

        ``relationship_filter`` is a pipe-separated list of relationship types
        (already validated upstream). Pass ``None`` to allow any.
        """
        if depth < 0 or depth > 10:
            raise ValueError("depth must be between 0 and 10")
        cypher = (
            "MATCH (seed:Entity {normalized_name: $name}) "
            "CALL apoc.path.subgraphAll(seed, { "
            "  maxLevel: $depth, relationshipFilter: $rel_filter "
            "}) YIELD nodes, relationships "
            "RETURN nodes, relationships"
        )
        with self.driver.session() as sess:
            row = sess.run(
                cypher,
                name=normalized_name,
                depth=depth,
                rel_filter=relationship_filter or "",
            ).single()
            if row is None:
                return {"nodes": [], "relationships": []}
            nodes_out = []
            for n in row["nodes"]:
                if "Entity" not in n.labels:
                    continue
                nodes_out.append(
                    {
                        "id": n.get("id"),
                        "type": n.get("type"),
                        "normalized_name": n.get("normalized_name"),
                        "name": n.get("name"),
                        "chunk_id": n.get("chunk_id"),
                        "source_document_id": n.get("source_document_id"),
                    }
                )
            rels_out = []
            for r in row["relationships"]:
                rt = r.type
                if rt == "DEFINED_IN":
                    continue
                start = r.start_node
                end = r.end_node
                rels_out.append(
                    {
                        "id": r.get("id"),
                        "source": start.get("normalized_name"),
                        "target": end.get("normalized_name"),
                        "relation": rt,
                        "confidence": r.get("confidence"),
                        "chunk_id": r.get("chunk_id"),
                    }
                )
            return {"nodes": nodes_out, "relationships": rels_out}
