"""Resolve the LLM model, key and endpoint from the environment (no side effects)."""

from __future__ import annotations

import os
from typing import Optional, Tuple

DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"
GROQ_OPENAI_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_GROQ_MODEL_NAME = "openai/gpt-oss-20b"
DEFAULT_OPENAI_MODEL_NAME = "gpt-4o-mini"


def get_env_value(name: str) -> Optional[str]:
    value = os.getenv(name)
    if value is None or not value.strip():
        return None
    return value


def resolve_llm_settings() -> Tuple[str, Optional[str], str]:
    """Return (model_name, api_key, base_url).

    - OpenAI (OPENAI_API_KEY and OPENAI_MODEL_NAME set):
      base_url = LLM_API_BASE or OPENAI_API_BASE or the OpenAI API.
    - Groq (GROQ_API_KEY set, the course default):
      base_url = LLM_API_BASE or the Groq OpenAI-compatible API.
      OPENAI_API_BASE is ignored here: docker-compose sets it to the OpenAI API
      for the embeddings, and a Groq key must never be sent to OpenAI.
    """
    openai_key = get_env_value("OPENAI_API_KEY")
    groq_key = get_env_value("GROQ_API_KEY")
    openai_model = get_env_value("OPENAI_MODEL_NAME")

    if openai_key and openai_model:
        base_url = get_env_value("LLM_API_BASE") or get_env_value("OPENAI_API_BASE") or DEFAULT_OPENAI_BASE_URL
        return openai_model, openai_key, base_url
    if groq_key:
        model_name = get_env_value("GROQ_MODEL_NAME") or DEFAULT_GROQ_MODEL_NAME
        base_url = get_env_value("LLM_API_BASE") or GROQ_OPENAI_BASE_URL
        return model_name, groq_key, base_url
    base_url = get_env_value("LLM_API_BASE") or get_env_value("OPENAI_API_BASE") or DEFAULT_OPENAI_BASE_URL
    return openai_model or DEFAULT_OPENAI_MODEL_NAME, openai_key, base_url
