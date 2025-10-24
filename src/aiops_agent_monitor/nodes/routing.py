"""Routing logic for the diagnostic LangGraph."""

from __future__ import annotations

import logging

from langchain_core.messages import AIMessage

from state import AgentState

logger = logging.getLogger(__name__)


def route_agent_decide(state: AgentState) -> str:
    """Return the next node depending on whether the LLM requested a tool."""
    last_message = state["messages"][-1] if state.get("messages") else None
    if isinstance(last_message, AIMessage) and getattr(last_message, "tool_calls", None):
        logger.info("Agent decided to use a tool. Routing to tool_executor.")
        return "tool_executor"

    logger.info("Agent produced a direct response. Routing to finalize_diagnosis.")
    return "finalize_diagnosis"
