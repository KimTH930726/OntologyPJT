from __future__ import annotations

import logging
import os

from app.integrations.llm.base import LLMProvider
from app.integrations.llm.fake_provider import FakeLLMProvider

logger = logging.getLogger(__name__)


def get_llm_provider() -> LLMProvider:
    """Pick a provider based on env. Falls back to FakeLLMProvider whenever
    required credentials are missing so local dev never breaks.
    """
    provider = (os.getenv("LLM_PROVIDER") or "fake").strip().lower()

    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        if not api_key:
            logger.warning("OPENAI_API_KEY missing, falling back to fake provider")
            return FakeLLMProvider()
        from app.integrations.llm.openai_provider import OpenAIProvider

        return OpenAIProvider(api_key=api_key, model=model)

    if provider == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY")
        model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
        if not api_key:
            logger.warning("ANTHROPIC_API_KEY missing, falling back to fake provider")
            return FakeLLMProvider()
        from app.integrations.llm.anthropic_provider import AnthropicProvider

        return AnthropicProvider(api_key=api_key, model=model)

    return FakeLLMProvider()
