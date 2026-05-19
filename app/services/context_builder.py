from __future__ import annotations

from dataclasses import dataclass

from app.services.graph_retriever import GraphRetrievalResult, GraphTriple
from app.services.vector_retriever import RetrievedChunk, VectorRetrievalResult


@dataclass
class BuiltContext:
    graph_block: str
    evidence_block: str
    used_chunks: list[RetrievedChunk]
    used_triples: list[GraphTriple]


class ContextBuilder:
    """Flatten Graph + Document context for the prompt with a simple char
    budget. Graph context wins ties (it is much smaller and central to
    GraphRAG)."""

    def __init__(self, total_budget_chars: int = 4000) -> None:
        if total_budget_chars <= 0:
            raise ValueError("total_budget_chars must be positive")
        self.total_budget_chars = total_budget_chars

    def build(
        self, graph: GraphRetrievalResult, vector: VectorRetrievalResult
    ) -> BuiltContext:
        graph_block, used_triples = self._render_graph(graph.triples)
        remaining = max(self.total_budget_chars - len(graph_block), 200)
        evidence_block, used_chunks = self._render_evidence(vector.chunks, remaining)
        return BuiltContext(
            graph_block=graph_block,
            evidence_block=evidence_block,
            used_chunks=used_chunks,
            used_triples=used_triples,
        )

    # --------------- private ---------------
    def _render_graph(self, triples: list[GraphTriple]) -> tuple[str, list[GraphTriple]]:
        if not triples:
            return "(없음)", []
        lines: list[str] = []
        used: list[GraphTriple] = []
        for t in triples:
            conf = (
                f" (confidence: {t.confidence:.2f})" if t.confidence is not None else ""
            )
            lines.append(f"- {t.source} {t.relation} {t.target}{conf}")
            used.append(t)
        return "\n".join(lines), used

    def _render_evidence(
        self, chunks: list[RetrievedChunk], budget: int
    ) -> tuple[str, list[RetrievedChunk]]:
        if not chunks:
            return "(없음)", []
        out: list[str] = []
        used: list[RetrievedChunk] = []
        consumed = 0
        for c in chunks:
            block = f"- chunk_id={c.chunk_id}:\n  {c.text}"
            if consumed + len(block) > budget and used:
                break
            out.append(block)
            used.append(c)
            consumed += len(block)
        return "\n".join(out), used
