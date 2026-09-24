"""Shared fixtures: fake models, no API key required."""
import os
from typing import Any

# Chapters 5-6: tool service URLs are only defined in microservices mode (see docker-compose.yml).
os.environ.setdefault("DEPLOYMENT_MODE", "microservices")

import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage


class ToolCallingFakeModel(GenericFakeChatModel):
    """GenericFakeChatModel that accepts bind_tools (called by create_agent)."""

    def bind_tools(self, tools: Any, **kwargs: Any) -> "ToolCallingFakeModel":
        return self


def tool_call(name: str, args: dict, call_id: str = "call_1") -> AIMessage:
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": call_id}])


@pytest.fixture
def fake_model():
    def _make(*messages):
        return ToolCallingFakeModel(messages=iter(list(messages)))
    return _make
