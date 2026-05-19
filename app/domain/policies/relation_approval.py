"""Pure domain policy: when can an extracted relation be APPROVED?

Isolated from infrastructure so the rule can be tested without a DB and
reused by both ReviewService and GraphSyncService (re-check at sync time).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.enums import ReviewStatus


@dataclass(frozen=True)
class _Endpoint:
    review_status: str


class RelationApprovalCode:
    OK = "OK"
    SOURCE_NOT_APPROVED = "SOURCE_NOT_APPROVED"
    TARGET_NOT_APPROVED = "TARGET_NOT_APPROVED"


def evaluate_relation_approval(source: object | None, target: object | None) -> tuple[bool, str]:
    """Return ``(can_approve, reason_code)``.

    ``source``/``target`` are any objects exposing a ``review_status`` attribute.
    """
    if source is None:
        return False, RelationApprovalCode.SOURCE_NOT_APPROVED
    if getattr(source, "review_status", None) != ReviewStatus.APPROVED.value:
        return False, RelationApprovalCode.SOURCE_NOT_APPROVED
    if target is None:
        return False, RelationApprovalCode.TARGET_NOT_APPROVED
    if getattr(target, "review_status", None) != ReviewStatus.APPROVED.value:
        return False, RelationApprovalCode.TARGET_NOT_APPROVED
    return True, RelationApprovalCode.OK
