from __future__ import annotations

import logging
from typing import Optional

from qdrant_client import QdrantClient

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_client: Optional[QdrantClient] = None


def get_qdrant_client() -> QdrantClient:
    global _client
    if _client is None:
        s = get_settings()
        _client = QdrantClient(url=s.qdrant_url)
    return _client


def ping_qdrant() -> tuple[bool, str | None]:
    try:
        client = get_qdrant_client()
        # get_collections does a real HTTP round-trip and is cheap.
        client.get_collections()
        return True, None
    except Exception as e:
        logger.warning("qdrant ping failed: %s", e)
        return False, str(e.__class__.__name__)


def close_qdrant_client() -> None:
    global _client
    if _client is not None:
        try:
            _client.close()
        except Exception:  # pragma: no cover
            pass
        _client = None
