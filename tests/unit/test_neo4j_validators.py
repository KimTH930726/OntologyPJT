from __future__ import annotations

import pytest

from app.repositories.neo4j_repository import (
    assert_safe_label,
    assert_safe_relation_type,
)


@pytest.mark.unit
class TestRelationTypeValidator:
    @pytest.mark.parametrize("name", ["REQUIRES", "APPLIES_TO", "PAID_BY", "A_B_C"])
    def test_accepts_allcaps(self, name: str) -> None:
        assert_safe_relation_type(name)  # no raise

    @pytest.mark.parametrize(
        "name",
        ["lower", "Order Item", "abc;DROP", "REL\\u0060BAD", "1ABC", "", "X" * 100],
    )
    def test_rejects_unsafe(self, name: str) -> None:
        with pytest.raises(ValueError):
            assert_safe_relation_type(name)


@pytest.mark.unit
class TestLabelValidator:
    @pytest.mark.parametrize("label", ["Policy", "OrderItem", "DocumentChunk", "Order", "A1"])
    def test_accepts_pascal_case(self, label: str) -> None:
        assert_safe_label(label)

    @pytest.mark.parametrize(
        "label", ["Order Item", "Abc;DROP", "1abc", "", "X" * 100, "Label`Bad"]
    )
    def test_rejects_unsafe_labels(self, label: str) -> None:
        with pytest.raises(ValueError):
            assert_safe_label(label)
