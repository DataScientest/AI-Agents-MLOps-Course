"""Fixtures partagées : modèles factices, aucune clé API requise."""
import os
from typing import Any

# Chapitres 5-6 : les URLs des services outils ne sont définies qu'en mode microservices (cf. docker-compose.yml).
os.environ.setdefault("DEPLOYMENT_MODE", "microservices")

import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage


class ToolCallingFakeModel(GenericFakeChatModel):
    """GenericFakeChatModel qui accepte bind_tools (appelé par create_agent)."""

    def bind_tools(self, tools: Any, **kwargs: Any) -> "ToolCallingFakeModel":
        return self


def tool_call(name: str, args: dict, call_id: str = "call_1") -> AIMessage:
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": call_id}])


@pytest.fixture
def fake_model():
    def _make(*messages):
        return ToolCallingFakeModel(messages=iter(list(messages)))
    return _make
