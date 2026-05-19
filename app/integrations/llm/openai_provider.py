"""Skeleton OpenAI provider.

Renders the Jinja2 prompts, calls Chat Completions with ``response_format=
json_object`` (or json_schema), and validates the result against
``ExtractionResponse``. Imports are lazy so missing dependencies / API keys
don't break W2.
"""
from __future__ import annotations

import json
import logging

from app.integrations.llm.base import LLMProvider, OntologySnapshot
from app.schemas.extraction import ExtractionResponse

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    provider_name = "openai"

    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def extract(self, chunk_text: str, snapshot: OntologySnapshot) -> ExtractionResponse:
        # Lazy import so the package isn't required for W2.
        from openai import OpenAI  # type: ignore

        from app.services.prompt_renderer import render_extraction_messages

        client = OpenAI(api_key=self.api_key)
        messages = render_extraction_messages(chunk_text, snapshot)

        resp = client.chat.completions.create(
            model=self.model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0,
        )
        raw = resp.choices[0].message.content or "{}"
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("openai returned non-JSON content: %s", raw[:200])
            payload = {"entities": [], "relations": []}
        return ExtractionResponse.model_validate(payload)
