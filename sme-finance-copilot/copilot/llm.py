"""
Pluggable language layer for rule-engine replies.

The copilot is fully functional with the deterministic TemplateNarrator (no
API key, no network).  When COPILOT_LLM_BASE_URL / _API_KEY / _MODEL are set,
open questions are handled by the full AI agent (copilot/ai_agent.py); this
narrator only rephrases rule-engine replies and must keep every number intact.
"""
from __future__ import annotations

import json
import os
import re
import urllib.request

from copilot import llm_config  # loads only local LLM settings once at startup

SYSTEM_PROMPT = (
    "You are SME Finance Copilot, a friendly finance assistant for ASEAN micro and small business owners. "
    "Rewrite the DRAFT into clear, plain language for the owner. Keep every number and currency exactly as given; use ¥ for CNY/RMB amounts and never convert or relabel currencies. "
    "Do not add facts, products, promises or approvals. Never state that credit is approved. "
    "Keep it under 180 words."
)


class TemplateNarrator:
    name = "template"

    def narrate(self, draft: str, context: dict | None = None) -> str:
        return draft


class OpenAICompatibleNarrator:
    name = "openai-compatible"

    def __init__(self, base_url: str, api_key: str, model: str, timeout: int = 20):
        self.base_url, self.api_key, self.model, self.timeout = base_url.rstrip("/"), api_key, model, timeout
        self.fallback = TemplateNarrator()

    def narrate(self, draft: str, context: dict | None = None) -> str:
        # Financial drafts are authoritative backend renderings. Arbitrary prose
        # rewriting cannot prove metric/source/period/approval integrity.
        # Gemini explanations use the separate typed claim verifier instead.
        return self.fallback.narrate(draft, context)


def get_narrator():
    url, key, model = (os.environ.get(k) for k in
                       ("COPILOT_LLM_BASE_URL", "COPILOT_LLM_API_KEY", "COPILOT_LLM_MODEL"))
    if url and key and model:
        return OpenAICompatibleNarrator(url, key, model)
    return TemplateNarrator()
