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


def _extract_section(prompt: str, header: str) -> str:
    """Return the slice of ``prompt`` starting after ``header`` until the next
    ``[Header]`` block. Used by the fake QA provider to inspect what the
    prompt builder produced."""
    idx = prompt.find(header)
    if idx == -1:
        return ""
    after = prompt[idx + len(header):]
    next_marker_idx = -1
    for i, ch in enumerate(after):
        if ch == "[" and (i == 0 or after[i - 1] == "\n"):
            # Skip past the marker itself if it's the very same header.
            next_marker_idx = i
            break
    if next_marker_idx == -1:
        return after.strip()
    return after[:next_marker_idx].strip()


_QUESTION_KEYWORD_TO_ENTITIES: dict[str, list[str]] = {
    "전체 취소": ["FullCancelPolicy"],
    "전체취소": ["FullCancelPolicy"],
    "FullCancelPolicy": ["FullCancelPolicy"],
    "부분 취소": ["PartialCancelPolicy"],
    "PartialCancelPolicy": ["PartialCancelPolicy"],
    "환불 금액": ["RefundAmountLimit"],
    "RefundAmountLimit": ["RefundAmountLimit"],
    "결제 완료": ["PaymentCompleted"],
    "PaymentCompleted": ["PaymentCompleted"],
    "배송 시작": ["DeliveryNotStarted"],
    "DeliveryNotStarted": ["DeliveryNotStarted"],
}


class FakeLLMProvider(LLMProvider):
    provider_name = "fake"
    model_name = "fake"

    # ---------- QA ----------
    def answer(self, prompt: str) -> str:
        graph_block = _extract_section(prompt, "[Graph Context]")
        evidence_block = _extract_section(prompt, "[Document Evidence]")
        question_block = _extract_section(prompt, "[User Question]")

        has_graph = graph_block.strip() and graph_block.strip() != "(없음)"
        has_evidence = evidence_block.strip() and evidence_block.strip() != "(없음)"

        cancel_question = any(
            k in question_block
            for k in ("환불", "취소", "전체 취소", "FullCancelPolicy")
        )
        has_payment_completed = "PaymentCompleted" in graph_block
        has_delivery_not_started = "DeliveryNotStarted" in graph_block

        if cancel_question and has_payment_completed and has_delivery_not_started:
            return (
                "결론: 제공된 근거 기준으로 결제 완료 후 배송 시작 전에는 주문 전체 취소가 가능합니다.\n"
                "근거: FullCancelPolicy가 PaymentCompleted와 DeliveryNotStarted를 요구하며, "
                "원문에도 동일한 정책이 명시되어 있습니다.\n"
                "후속 액션: 실제 주문의 결제 상태와 배송 상태를 확인해야 합니다."
            )

        if not has_graph and not has_evidence:
            return "근거 부족: 제공된 Graph Context와 Document Evidence만으로는 판단할 수 없습니다."

        return (
            "결론: 제공된 근거에 따라 답변합니다.\n"
            "근거: 위 Graph Context와 Document Evidence를 참고했습니다.\n"
            "후속 액션: 정확한 판단이 필요하면 관련 정책 문서를 추가 확인하세요."
        )

    def extract_intent_entities(self, question: str) -> list[str]:
        found: list[str] = []
        for keyword, mapped in _QUESTION_KEYWORD_TO_ENTITIES.items():
            if keyword in question:
                for n in mapped:
                    if n not in found:
                        found.append(n)
        return found

    # ---------- extraction (W2) ----------
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
