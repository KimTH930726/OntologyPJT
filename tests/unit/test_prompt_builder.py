"""PromptBuilder falls back to the bundled .j2 file when no active DB
version exists, so the QA pipeline works even before the seed runs."""

from __future__ import annotations

import pytest

from app.services.context_builder import BuiltContext
from app.services.prompt_builder import PromptBuilder


class _FakePromptRepo:
    def __init__(self) -> None:
        self.active = None

    def get_active_version_by_name(self, name: str):  # noqa: ARG002, ANN201
        return self.active


@pytest.mark.unit
class TestPromptBuilderFileFallback:
    def test_falls_back_to_bundled_template(self) -> None:
        ctx = BuiltContext(
            graph_block="- A REQUIRES B",
            evidence_block="- chunk_id=c1:\n  hi",
            used_chunks=[],
            used_triples=[],
        )
        pb = PromptBuilder(db=None, repo=_FakePromptRepo())  # type: ignore[arg-type]
        rendered = pb.build_qa(ctx, "Q?")
        assert "[System]" in rendered
        assert "[Graph Context]" in rendered
        assert "- A REQUIRES B" in rendered
        assert "[Document Evidence]" in rendered
        assert "chunk_id=c1" in rendered
        assert "Q?" in rendered

    def test_uses_active_version_when_available(self) -> None:
        class _ActiveVersion:
            content = "GRAPH={{ graph_block }} | Q={{ question }}"

        repo = _FakePromptRepo()
        repo.active = _ActiveVersion()
        ctx = BuiltContext(
            graph_block="(없음)",
            evidence_block="(없음)",
            used_chunks=[],
            used_triples=[],
        )
        rendered = PromptBuilder(db=None, repo=repo).build_qa(ctx, "X")  # type: ignore[arg-type]
        assert rendered.strip() == "GRAPH=(없음) | Q=X"
