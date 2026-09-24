"""LangGraph node responsible for LLM + tool orchestration."""

from __future__ import annotations

import logging
from typing import Iterable, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import BaseTool

from guardrails import current_run_messages
from nodes.routing import FINALIZE_RESERVED_STEPS
from prompts import LAST_STEP_INSTRUCTION
from state import AgentState

logger = logging.getLogger(__name__)

# HTTP statuses the LLM provider uses for quota problems:
# 429 = rate limit (requests/tokens per minute or per day), 413 = request larger than the TPM limit.
RATE_LIMIT_STATUS_CODES = (413, 429)


class LLMRateLimitError(RuntimeError):
    """The LLM provider refused the request because of a rate limit or quota."""

    def __init__(self, message: str, provider_status: Optional[int] = None):
        super().__init__(message)
        self.provider_status = provider_status


def rate_limit_status(exc: Exception) -> Optional[int]:
    """Return 429/413 if exc is a provider rate-limit error, else None."""
    status = getattr(exc, "status_code", None)
    if status in RATE_LIMIT_STATUS_CODES:
        return status
    text = str(exc).lower()
    if "rate_limit" in text or "rate limit" in text or "error code: 429" in text:
        return 429
    if "error code: 413" in text:
        return 413
    return None


def llm_agent_node(
    llm: BaseChatModel,
    tools: Iterable[BaseTool],
    system_prompt: str,
):
    """Return a callable that runs the LLM with the provided toolset."""

    prompt = ChatPromptTemplate.from_messages(
        [SystemMessage(content=system_prompt), ("placeholder", "{messages}")]
    )
    llm_with_tools = llm.bind_tools(list(tools))
    llm_chain = prompt | llm_with_tools

    def _node(state: AgentState) -> AgentState:
        logger.info("Node 'llm_agent_node': processing alert %s", state.get("alert_info"))
        # Only the current diagnosis run goes to the LLM: the checkpointed thread
        # keeps earlier runs of the same alert fingerprint, which would grow the prompt forever.
        messages = current_run_messages(state["messages"])
        remaining = state.get("remaining_steps")
        if remaining is not None and remaining <= FINALIZE_RESERVED_STEPS:
            # Last LLM call before the step limit: the router would skip a tool call
            # (degraded answer), so ask the model for its diagnosis now. The note is
            # sent to the LLM only, not stored in the graph state.
            logger.info("Last step (remaining_steps=%s): asking the LLM to answer without tools.", remaining)
            messages = messages + [HumanMessage(content=LAST_STEP_INSTRUCTION)]
        try:
            result: BaseMessage = llm_chain.invoke({"messages": messages})
        except Exception as e:
            status = rate_limit_status(e)
            if status is not None:
                # Do not turn a quota error into a fake diagnosis: stop the run and
                # let the endpoint answer with an explicit "LLM rate limited" error.
                logger.error("LLM rate limited (provider HTTP %s): %s", status, e)
                raise LLMRateLimitError(
                    f"LLM rate limited (provider HTTP {status}): {e}", provider_status=status
                ) from e
            logger.error("Error in llm_agent_node: %s", e)
            raise
        logger.info("LLM produced result: %s", result)
        return {"messages": [result]}

    return _node
