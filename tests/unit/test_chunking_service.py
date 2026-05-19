from __future__ import annotations

import pytest

from app.services.chunking_service import ChunkingService


@pytest.mark.unit
class TestChunkingService:
    def test_three_sentences_produce_three_chunks(self) -> None:
        text = (
            "결제 완료 후 배송 시작 전에는 주문 전체 취소가 가능하다. "
            "부분 취소는 주문상품 단위로만 가능하다. "
            "환불 금액은 실제 결제 금액을 초과할 수 없다."
        )
        drafts = ChunkingService().split(text)
        assert len(drafts) == 3
        assert all(d.token_count > 0 for d in drafts)
        assert [d.index for d in drafts] == [0, 1, 2]

    def test_empty_input_returns_no_chunks(self) -> None:
        assert ChunkingService().split("") == []
        assert ChunkingService().split("   \n\n  ") == []

    def test_long_sentence_is_hard_split(self) -> None:
        svc = ChunkingService(max_chars=20)
        long = "A" * 100  # 1 sentence, 100 chars, > 2 * max_chars
        drafts = svc.split(long)
        assert len(drafts) > 1
        assert all(len(d.text) <= 20 for d in drafts)

    def test_invalid_max_chars_raises(self) -> None:
        with pytest.raises(ValueError):
            ChunkingService(max_chars=0)
