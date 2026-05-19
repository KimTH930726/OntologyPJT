from __future__ import annotations

import logging
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchAny,
    PointStruct,
    VectorParams,
)

from app.core.config import get_settings
from app.db.qdrant import get_qdrant_client

logger = logging.getLogger(__name__)

VECTOR_DIM = 384


class QdrantRepository:
    """Thin wrapper over QdrantClient for the chunk collection."""

    def __init__(self, client: QdrantClient | None = None, collection: str | None = None) -> None:
        self.client = client or get_qdrant_client()
        self.collection = collection or get_settings().qdrant_collection
        self._ensured = False

    def ensure_collection(self) -> None:
        if self._ensured:
            return
        existing = {c.name for c in self.client.get_collections().collections}
        if self.collection not in existing:
            logger.info("creating qdrant collection %s (dim=%d)", self.collection, VECTOR_DIM)
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
            )
        self._ensured = True

    def upsert_point(self, point_id: str, vector: list[float], payload: dict[str, Any]) -> None:
        self.ensure_collection()
        self.client.upsert(
            collection_name=self.collection,
            points=[PointStruct(id=point_id, vector=vector, payload=payload)],
        )

    def upsert_points(self, items: list[tuple[str, list[float], dict[str, Any]]]) -> None:
        """Batch upsert: one HTTP round-trip instead of N. Caller handles
        per-item error semantics by chunking the input or splitting on
        retry."""
        if not items:
            return
        self.ensure_collection()
        self.client.upsert(
            collection_name=self.collection,
            points=[
                PointStruct(id=pid, vector=vec, payload=payload) for pid, vec, payload in items
            ],
        )

    def search(
        self,
        vector: list[float],
        top_k: int = 5,
        chunk_id_in: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        self.ensure_collection()
        query_filter: Filter | None = None
        if chunk_id_in:
            query_filter = Filter(
                must=[FieldCondition(key="chunk_id", match=MatchAny(any=list(chunk_id_in)))]
            )
        try:
            results = self.client.search(
                collection_name=self.collection,
                query_vector=vector,
                query_filter=query_filter,
                limit=top_k,
                with_payload=True,
            )
        except UnexpectedResponse as e:  # pragma: no cover
            logger.warning("qdrant search failed: %s", e)
            return []
        return [{"id": str(p.id), "score": p.score, "payload": p.payload or {}} for p in results]

    def get_point(self, point_id: str) -> dict[str, Any] | None:
        try:
            self.ensure_collection()
            points = self.client.retrieve(
                collection_name=self.collection,
                ids=[point_id],
                with_payload=True,
                with_vectors=False,
            )
        except UnexpectedResponse as e:  # pragma: no cover
            logger.warning("qdrant retrieve failed: %s", e)
            return None
        if not points:
            return None
        p = points[0]
        return {"id": str(p.id), "payload": p.payload or {}}
