"""Routing logic for the diagnostic LangGraph."""

from __future__ import annotations

import logging

from langchain_core.messages import AIMessage

from state import AgentState

logger = logging.getLogger(__name__)

# A tool call costs 3 more steps before the graph can end: the tool, the next LLM
# call and the final summary. When no more than that remains before
# AGENT_RECURSION_LIMIT, the tool call is skipped and the agent writes its diagnosis
# with the data already collected (the API response is then "degraded").
FINALIZE_RESERVED_STEPS = 3


def route_agent_decide(state: AgentState) -> str:
    """Return the next node depending on whether the LLM requested a tool."""
    last_message = state["messages"][-1] if state.get("messages") else None
    if isinstance(last_message, AIMessage) and getattr(last_message, "tool_calls", None):
        remaining = state.get("remaining_steps")
        if remaining is not None and remaining <= FINALIZE_RESERVED_STEPS:
            logger.warning(
                "Step limit almost reached (remaining_steps=%s): skipping the tool call, "
                "routing to finalize_diagnosis with the data collected so far.",
                remaining,
            )
            return "finalize_diagnosis"
        logger.info("Agent decided to use a tool. Routing to tool_executor.")
        return "tool_executor"

    logger.info("Agent produced a direct response. Routing to finalize_diagnosis.")
    return "finalize_diagnosis"
