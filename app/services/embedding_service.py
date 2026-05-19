from __future__ import annotations

import hashlib
import struct

VECTOR_DIM = 384


class EmbeddingService:
    """Deterministic fake embedding for W1.

    같은 입력 → 같은 벡터. SHA-256 기반으로 384개의 float를 채우고 L2 정규화한다.
    실제 임베딩 모델은 W4 이후 LLM 연동 단계에서 교체.
    """

    def __init__(self, dim: int = VECTOR_DIM) -> None:
        if dim <= 0:
            raise ValueError("dim must be positive")
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        normalized = text.strip().lower()
        out: list[float] = []
        counter = 0
        while len(out) < self.dim:
            digest = hashlib.sha256(f"{normalized}|{counter}".encode()).digest()
            for i in range(0, 32, 4):
                if len(out) >= self.dim:
                    break
                raw = struct.unpack("<i", digest[i : i + 4])[0]
                out.append(raw / 2_147_483_648.0)  # roughly in [-1, 1)
            counter += 1

        # L2 normalize so cosine similarity is well-behaved.
        norm = sum(x * x for x in out) ** 0.5
        if norm == 0:
            return out
        return [x / norm for x in out]
