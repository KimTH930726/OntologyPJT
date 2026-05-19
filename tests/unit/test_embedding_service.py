from __future__ import annotations

import math

import pytest

from app.services.embedding_service import VECTOR_DIM, EmbeddingService


@pytest.mark.unit
class TestEmbeddingService:
    def test_default_dimension(self) -> None:
        vec = EmbeddingService().embed("hello")
        assert len(vec) == VECTOR_DIM == 384

    def test_deterministic_same_input(self) -> None:
        a = EmbeddingService().embed("결제 완료")
        b = EmbeddingService().embed("결제 완료")
        assert a == b

    def test_different_input_diverges(self) -> None:
        a = EmbeddingService().embed("foo")
        b = EmbeddingService().embed("bar")
        assert a != b

    def test_l2_normalized(self) -> None:
        v = EmbeddingService().embed("normalize me")
        norm = math.sqrt(sum(x * x for x in v))
        assert math.isclose(norm, 1.0, rel_tol=1e-6)

    def test_invalid_dim_raises(self) -> None:
        with pytest.raises(ValueError):
            EmbeddingService(dim=0)
