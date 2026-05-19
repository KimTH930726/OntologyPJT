from __future__ import annotations

import pytest

from app.integrations.llm.base import OntologySnapshot
from app.integrations.llm.fake_provider import FakeLLMProvider

EMPTY_SNAPSHOT = OntologySnapshot(entity_types=(), relation_types=())


@pytest.fixture
def provider() -> FakeLLMProvider:
    return FakeLLMProvider()


@pytest.mark.unit
class TestFakeExtraction:
    def test_full_cancel_rule(self, provider: FakeLLMProvider) -> None:
        text = "결제 완료 후 배송 시작 전에는 주문 전체 취소가 가능하다."
        out = provider.extract(text, EMPTY_SNAPSHOT)
        names = {e.normalized_name for e in out.entities}
        assert {"FullCancelPolicy", "PaymentCompleted", "DeliveryNotStarted"} <= names
        rels = {(r.source, r.relation, r.target) for r in out.relations}
        assert ("FullCancelPolicy", "REQUIRES", "PaymentCompleted") in rels
        assert ("FullCancelPolicy", "APPLIES_TO", "Order") in rels

    def test_refund_rule_includes_intentional_violation(self, provider: FakeLLMProvider) -> None:
        # The fake provider emits one intentional `Policy APPLIES_TO Refund`
        # which is NOT in the seed (only `Policy APPLIES_TO Order`).
        text = "환불 금액은 실제 결제 금액을 초과할 수 없다."
        out = provider.extract(text, EMPTY_SNAPSHOT)
        triple = ("RefundAmountLimit", "APPLIES_TO", "Refund")
        emitted = {(r.source, r.relation, r.target) for r in out.relations}
        assert triple in emitted

    def test_unrelated_text_returns_empty(self, provider: FakeLLMProvider) -> None:
        out = provider.extract("아무 의미 없는 텍스트", EMPTY_SNAPSHOT)
        assert out.entities == []
        assert out.relations == []


@pytest.mark.unit
class TestFakeQA:
    def test_positive_answer_when_graph_has_payment_and_delivery(
        self, provider: FakeLLMProvider
    ) -> None:
        prompt = (
            "[Graph Context]\n"
            "- FullCancelPolicy REQUIRES PaymentCompleted (confidence: 0.90)\n"
            "- FullCancelPolicy REQUIRES DeliveryNotStarted (confidence: 0.88)\n"
            "[Document Evidence]\n"
            "- chunk_id=c1:\n  결제 완료 후 ...\n"
            "[User Question]\n"
            "배송 시작 전 결제 완료 주문은 전체 취소 가능한가?\n"
        )
        ans = provider.answer(prompt)
        assert "전체 취소가 가능" in ans
        assert "근거" in ans
        assert "후속 액션" in ans

    def test_no_context_returns_evidence_missing_phrase(self, provider: FakeLLMProvider) -> None:
        prompt = (
            "[Graph Context]\n(없음)\n[Document Evidence]\n(없음)\n[User Question]\n무관한 질문\n"
        )
        ans = provider.answer(prompt)
        assert "근거 부족" in ans

    def test_generic_answer_when_only_evidence_present(self, provider: FakeLLMProvider) -> None:
        prompt = (
            "[Graph Context]\n(없음)\n"
            "[Document Evidence]\n- chunk_id=x:\n  some text\n"
            "[User Question]\n어떤 질문\n"
        )
        ans = provider.answer(prompt)
        assert "근거 부족" not in ans
        assert "결론" in ans


@pytest.mark.unit
class TestFakeIntent:
    def test_keyword_mapping(self, provider: FakeLLMProvider) -> None:
        seeds = provider.extract_intent_entities(
            "배송 시작 전 결제 완료 주문은 전체 취소 가능한가?"
        )
        assert "FullCancelPolicy" in seeds
        assert "PaymentCompleted" in seeds
        assert "DeliveryNotStarted" in seeds

    def test_unknown_question_returns_empty(self, provider: FakeLLMProvider) -> None:
        assert provider.extract_intent_entities("XYZ ABC") == []
