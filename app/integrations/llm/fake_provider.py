"""Deterministic fake LLM provider for offline development / tests.

It emits entities/relations based on keyword matches in the chunk text. Some
emissions intentionally violate the ontology seed (e.g. ``APPLIES_TO Refund``)
so that the SCHEMA_VIOLATION path is exercised end-to-end.
"""
from __future__ import annotations

from app.integrations.llm.base import LLMProvider, OntologySnapshot
from app.schemas.extraction import (
    ExtractionResponse,
    LLMEntityCandidate,
    LLMRelationCandidate,
)


class FakeLLMProvider(LLMProvider):
    provider_name = "fake"

    def extract(self, chunk_text: str, snapshot: OntologySnapshot) -> ExtractionResponse:
        entities: list[LLMEntityCandidate] = []
        relations: list[LLMRelationCandidate] = []

        text = chunk_text.strip()

        # Rule 1: 전체 취소 정책
        if "전체 취소" in text or ("결제 완료" in text and "배송" in text):
            entities += [
                LLMEntityCandidate(
                    name="전체 취소 정책",
                    type="Policy",
                    normalized_name="FullCancelPolicy",
                    confidence=0.91,
                    evidence_text=text,
                ),
                LLMEntityCandidate(
                    name="결제 완료",
                    type="Condition",
                    normalized_name="PaymentCompleted",
                    confidence=0.89,
                    evidence_text=text,
                ),
                LLMEntityCandidate(
                    name="배송 시작 전",
                    type="Condition",
                    normalized_name="DeliveryNotStarted",
                    confidence=0.87,
                    evidence_text=text,
                ),
            ]
            relations += [
                LLMRelationCandidate(
                    source="FullCancelPolicy", source_type="Policy",
                    relation="REQUIRES",
                    target="PaymentCompleted", target_type="Condition",
                    confidence=0.90, evidence_text=text,
                ),
                LLMRelationCandidate(
                    source="FullCancelPolicy", source_type="Policy",
                    relation="REQUIRES",
                    target="DeliveryNotStarted", target_type="Condition",
                    confidence=0.88, evidence_text=text,
                ),
                LLMRelationCandidate(
                    source="FullCancelPolicy", source_type="Policy",
                    relation="APPLIES_TO",
                    target="Order", target_type="Order",
                    confidence=0.85, evidence_text=text,
                ),
            ]

        # Rule 2: 부분 취소
        if "부분 취소" in text:
            entities += [
                LLMEntityCandidate(
                    name="부분 취소 정책",
                    type="Policy",
                    normalized_name="PartialCancelPolicy",
                    confidence=0.88,
                    evidence_text=text,
                ),
                LLMEntityCandidate(
                    name="주문상품 단위",
                    type="Condition",
                    normalized_name="PerOrderItemOnly",
                    confidence=0.82,
                    evidence_text=text,
                ),
            ]
            relations += [
                LLMRelationCandidate(
                    source="PartialCancelPolicy", source_type="Policy",
                    relation="APPLIES_TO",
                    target="Order", target_type="Order",
                    confidence=0.83, evidence_text=text,
                ),
                LLMRelationCandidate(
                    source="PartialCancelPolicy", source_type="Policy",
                    relation="REQUIRES",
                    target="PerOrderItemOnly", target_type="Condition",
                    confidence=0.80, evidence_text=text,
                ),
            ]

        # Rule 3: 환불 금액
        if "환불 금액" in text or "환불금액" in text:
            entities += [
                LLMEntityCandidate(
                    name="환불 금액 상한 정책",
                    type="Policy",
                    normalized_name="RefundAmountLimit",
                    confidence=0.86,
                    evidence_text=text,
                ),
                LLMEntityCandidate(
                    name="결제 금액 한도",
                    type="Condition",
                    normalized_name="PaymentAmountCap",
                    confidence=0.81,
                    evidence_text=text,
                ),
            ]
            relations += [
                LLMRelationCandidate(
                    source="RefundAmountLimit", source_type="Policy",
                    relation="REQUIRES",
                    target="PaymentAmountCap", target_type="Condition",
                    confidence=0.78, evidence_text=text,
                ),
                # Intentional schema violation: "Policy APPLIES_TO Refund" is
                # NOT in the seed (only Policy APPLIES_TO Order is allowed).
                # This exercises the SCHEMA_VIOLATION reject path.
                LLMRelationCandidate(
                    source="RefundAmountLimit", source_type="Policy",
                    relation="APPLIES_TO",
                    target="Refund", target_type="Refund",
                    confidence=0.60, evidence_text=text, needs_review=True,
                ),
            ]

        return ExtractionResponse(entities=entities, relations=relations)
