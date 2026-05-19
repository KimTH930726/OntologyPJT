from __future__ import annotations

import re
from dataclasses import dataclass

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?。])\s+")


@dataclass(frozen=True)
class ChunkDraft:
    index: int
    text: str
    token_count: int


class ChunkingService:
    """Sentence-grouped, character-bounded splitter.

    MVP: 한국어/영문 혼용 문서를 문장 단위로 자르고 max_chars 한도 안에서 묶는다.
    토큰 카운트는 공백 분리 기준 근사치(영문 우세) + 한글은 글자수 / 2.5 가산.
    """

    def __init__(self, max_chars: int = 400) -> None:
        if max_chars <= 0:
            raise ValueError("max_chars must be positive")
        self.max_chars = max_chars

    def split(self, text: str) -> list[ChunkDraft]:
        """Sentence per chunk; hard-split sentences longer than 2x max_chars."""
        text = text.strip()
        if not text:
            return []

        sentences = [s.strip() for s in _SENTENCE_SPLIT.split(text) if s.strip()]
        if not sentences:
            sentences = [text]

        final: list[str] = []
        for s in sentences:
            if len(s) <= self.max_chars * 2:
                final.append(s)
            else:
                for i in range(0, len(s), self.max_chars):
                    final.append(s[i : i + self.max_chars])

        return [
            ChunkDraft(index=i, text=t, token_count=self._estimate_tokens(t))
            for i, t in enumerate(final)
        ]

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        if not text:
            return 0
        words = len(text.split())
        hangul = sum(1 for ch in text if "가" <= ch <= "힣")
        return max(1, words + int(hangul / 2.5))
