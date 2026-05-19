from __future__ import annotations

import pytest

from app.services.context_builder import ContextBuilder
from app.services.graph_retriever import GraphRetrievalResult, GraphTriple
from app.services.vector_retriever import RetrievedChunk, VectorRetrievalResult


def _graph(*triples: GraphTriple) -> GraphRetrievalResult:
    return GraphRetrievalResult(triples=list(triples))


def _vector(*chunks: RetrievedChunk) -> VectorRetrievalResult:
    return VectorRetrievalResult(chunks=list(chunks))


@pytest.mark.unit
class TestContextBuilder:
    def test_empty_inputs_produce_marker(self) -> None:
        ctx = ContextBuilder().build(_graph(), _vector())
        assert ctx.graph_block == "(없음)"
        assert ctx.evidence_block == "(없음)"
        assert ctx.used_triples == []
        assert ctx.used_chunks == []

    def test_triples_are_rendered_with_confidence(self) -> None:
        ctx = ContextBuilder().build(
            _graph(GraphTriple("A", "REQUIRES", "B", 0.9, "c1")),
            _vector(),
        )
        assert "A REQUIRES B" in ctx.graph_block
        assert "0.90" in ctx.graph_block

    def test_evidence_block_includes_chunk_ids_and_text(self) -> None:
        ctx = ContextBuilder().build(
            _graph(),
            _vector(RetrievedChunk("c1", "d1", "원문 내용", "graph_evidence")),
        )
        assert "chunk_id=c1" in ctx.evidence_block
        assert "원문 내용" in ctx.evidence_block

    def test_evidence_respects_char_budget(self) -> None:
        big = "x" * 1000
        cb = ContextBuilder(total_budget_chars=600)
        ctx = cb.build(
            _graph(GraphTriple("A", "R", "B", 0.5, "c0")),
            _vector(
                RetrievedChunk("c1", "d1", big, "vector_search"),
                RetrievedChunk("c2", "d1", big, "vector_search"),
                RetrievedChunk("c3", "d1", big, "vector_search"),
            ),
        )
        # Should keep at least one (always renders the first), and stop after
        # the budget is exhausted.
        assert len(ctx.used_chunks) >= 1
        assert len(ctx.used_chunks) < 3
