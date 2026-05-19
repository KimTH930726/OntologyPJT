"""Skeleton Anthropic (Claude) provider.

Uses the messages API with a JSON-output instruction. Validates the response
against ``ExtractionResponse``. Imports are lazy.
"""
from __future__ import annotations

import json
import logging
import re

from app.integrations.llm.base import LLMProvider, OntologySnapshot
from app.schemas.extraction import ExtractionResponse

logger = logging.getLogger(__name__)

_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)


class AnthropicProvider(LLMProvider):
    provider_name = "anthropic"

    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def extract(self, chunk_text: str, snapshot: OntologySnapshot) -> ExtractionResponse:
        from anthropic import Anthropic  # type: ignore

        from app.services.prompt_renderer import render_extraction_for_anthropic

        client = Anthropic(api_key=self.api_key)
        system, user = render_extraction_for_anthropic(chunk_text, snapshot)

        resp = client.messages.create(
            model=self.model,
            max_tokens=2000,
            system=system,
            messages=[{"role": "user", "content": user}],
            temperature=0,
        )
        text = "".join(
            block.text for block in resp.content if getattr(block, "type", None) == "text"
        )
        match = _JSON_BLOCK.search(text)
        raw = match.group(0) if match else "{}"
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("anthropic returned non-JSON content: %s", text[:200])
            payload = {"entities": [], "relations": []}
        return ExtractionResponse.model_validate(payload)
