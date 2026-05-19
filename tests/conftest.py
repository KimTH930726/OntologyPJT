"""Test bootstrap.

We deliberately set placeholder env vars before app imports run, so that
Pydantic Settings won't reach for live infrastructure during pure unit tests.
Anything that genuinely needs Postgres/Neo4j/Qdrant should be marked
``invariant`` and use the dedicated mocks in ``tests/unit/test_*``.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure ``app`` package is importable when pytest is invoked from anywhere.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://test:test@localhost:5432/test")
os.environ.setdefault("NEO4J_URI", "bolt://localhost:7687")
os.environ.setdefault("NEO4J_USER", "neo4j")
os.environ.setdefault("NEO4J_PASSWORD", "password")
os.environ.setdefault("QDRANT_URL", "http://localhost:6333")
os.environ.setdefault("QDRANT_COLLECTION", "chunks")
os.environ.setdefault("LLM_PROVIDER", "fake")
os.environ.setdefault("EMBED_PROVIDER", "fake")
