from __future__ import annotations

import pytest

from app.domain.enums import ReviewStatus
from app.domain.policies.relation_approval import (
    RelationApprovalCode,
    evaluate_relation_approval,
)


class _Endpoint:
    def __init__(self, status: str) -> None:
        self.review_status = status


APPROVED = _Endpoint(ReviewStatus.APPROVED.value)
PENDING = _Endpoint(ReviewStatus.PENDING.value)
REJECTED = _Endpoint(ReviewStatus.REJECTED.value)


@pytest.mark.unit
@pytest.mark.invariant
class TestRelationApprovalPolicy:
    """Locks down: relation approve requires BOTH endpoints APPROVED."""

    def test_both_approved_passes(self) -> None:
        ok, code = evaluate_relation_approval(APPROVED, APPROVED)
        assert ok and code == RelationApprovalCode.OK

    def test_source_pending_blocks(self) -> None:
        ok, code = evaluate_relation_approval(PENDING, APPROVED)
        assert not ok and code == RelationApprovalCode.SOURCE_NOT_APPROVED

    def test_target_rejected_blocks(self) -> None:
        ok, code = evaluate_relation_approval(APPROVED, REJECTED)
        assert not ok and code == RelationApprovalCode.TARGET_NOT_APPROVED

    def test_missing_source_blocks(self) -> None:
        ok, code = evaluate_relation_approval(None, APPROVED)
        assert not ok and code == RelationApprovalCode.SOURCE_NOT_APPROVED

    def test_missing_target_blocks(self) -> None:
        ok, code = evaluate_relation_approval(APPROVED, None)
        assert not ok and code == RelationApprovalCode.TARGET_NOT_APPROVED

    def test_both_missing_blocks_at_source_first(self) -> None:
        ok, code = evaluate_relation_approval(None, None)
        assert not ok and code == RelationApprovalCode.SOURCE_NOT_APPROVED
