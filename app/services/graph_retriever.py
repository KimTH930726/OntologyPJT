from __future__ import annotations

import logging
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.integrations.llm.base import LLMProvider
from app.integrations.llm.factory import get_llm_provider
from app.repositories.neo4j_repository import Neo4jRepository
from app.repositories.ontology_repository import OntologyRepository

logger = logging.getLogger(__name__)


@dataclass
class GraphTriple:
    source: str
    relation: str
    target: str
    confidence: float | None = None
    chunk_id: str | None = None


@dataclass
class GraphRetrievalResult:
    seed_entities: list[str] = field(default_factory=list)
    triples: list[GraphTriple] = field(default_factory=list)
    evidence_chunk_ids: list[str] = field(default_factory=list)
    nodes: list[dict] = field(default_factory=list)


class GraphRetriever:
    """Resolve seed entities from the question, then pull a depth-bounded
    subgraph from Neo4j. Falls back gracefully to an empty result when no
    seed can be resolved or when Neo4j is unavailable."""

    def __init__(
        self,
        db: Session,
        *,
        neo4j_repo: Neo4jRepository | None = None,
        ontology_repo: OntologyRepository | None = None,
        provider: LLMProvider | None = None,
    ) -> None:
        self.db = db
        self.neo4j = neo4j_repo or Neo4jRepository()
        self.ontology = ontology_repo or OntologyRepository(db)
        self.provider = provider or get_llm_provider()

    def retrieve(self, question: str, depth: int = 2) -> GraphRetrievalResult:
        seeds = self._resolve_seeds(question)
        if not seeds:
            return GraphRetrievalResult()

        whitelist = [
            rt.relation_name
            for rt in self.ontology.list_relation_types(active_only=True)
        ]
        rel_filter = "|".join(sorted(set(whitelist))) if whitelist else None

        all_nodes: dict[str, dict] = {}
        triples: list[GraphTriple] = []
        evidence: set[str] = set()

        for seed in seeds:
            try:
                sub = self.neo4j.fetch_subgraph(seed, depth, rel_filter)
            except Exception as e:
                logger.warning("subgraph fetch failed for seed=%s: %s", seed, e)
                continue

            for node in sub["nodes"]:
                key = node.get("normalized_name") or str(node.get("id"))
                if key not in all_nodes:
                    all_nodes[key] = node
                cid = node.get("chunk_id")
                if cid:
                    evidence.add(str(cid))

            for rel in sub["relationships"]:
                cid = rel.get("chunk_id")
                if cid:
                    evidence.add(str(cid))
                triples.append(
                    GraphTriple(
                        source=rel["source"],
                        relation=rel["relation"],
                        target=rel["target"],
                        confidence=(
                            float(rel["confidence"])
                            if rel.get("confidence") is not None
                            else None
                        ),
                        chunk_id=str(cid) if cid else None,
                    )
                )

        triples = _dedupe_triples(triples)
        return GraphRetrievalResult(
            seed_entities=seeds,
            triples=triples,
            evidence_chunk_ids=sorted(evidence),
            nodes=list(all_nodes.values()),
        )

    # --------------- seeds ---------------
    def _resolve_seeds(self, question: str) -> list[str]:
        # 1) Direct match against Neo4j normalized_name.
        try:
            names = self.neo4j.list_normalized_names()
        except Exception as e:
            logger.warning("neo4j name listing failed: %s", e)
            names = []
        matched = [n for n in names if n and n in question]

        # 2) Fallback: ask the provider for intent entities.
        if not matched:
            try:
                hints = self.provider.extract_intent_entities(question)
            except Exception as e:
                logger.warning("provider intent extraction failed: %s", e)
                hints = []
            for n in hints:
                if names and n not in names:
                    continue
                if n not in matched:
                    matched.append(n)

        return matched


def _dedupe_triples(triples: list[GraphTriple]) -> list[GraphTriple]:
    seen: set[tuple[str, str, str]] = set()
    out: list[GraphTriple] = []
    for t in triples:
        key = (t.source, t.relation, t.target)
        if key in seen:
            continue
        seen.add(key)
        out.append(t)
    return out
