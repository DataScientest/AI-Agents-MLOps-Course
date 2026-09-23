"""Guardrails for the diagnostic agent loop.

- AGENT_RECURSION_LIMIT caps the number of LangGraph steps of one diagnosis
  (one LLM call or one tool execution = one step). Close to the limit, the
  router skips the next tool call and the agent writes its diagnosis with the
  data already collected; the API then answers with status "degraded".
- TOOL_OUTPUT_MAX_CHARS caps the size of each tool result sent back to the LLM.
- Only the messages of the current diagnosis run are sent to the LLM, even when
  the checkpointed thread (thread_id derived from the alert fingerprint) holds
  the history of earlier runs.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, Sequence, Tuple

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langgraph.errors import GraphRecursionError

logger = logging.getLogger(__name__)

DEFAULT_RECURSION_LIMIT = 12
DEFAULT_TOOL_OUTPUT_MAX_CHARS = 2000


def _int_from_env(name: str, default: int) -> int:
    value = os.getenv(name)
    try:
        return int(value) if value and value.strip() else default
    except ValueError:
        logger.warning("Invalid %s=%r, using default %s", name, value, default)
        return default


def get_recursion_limit() -> int:
    """Maximum number of graph steps for one diagnosis (env AGENT_RECURSION_LIMIT)."""
    return _int_from_env("AGENT_RECURSION_LIMIT", DEFAULT_RECURSION_LIMIT)


def get_tool_output_max_chars() -> int:
    """Maximum size of one tool result sent to the LLM (env TOOL_OUTPUT_MAX_CHARS)."""
    return _int_from_env("TOOL_OUTPUT_MAX_CHARS", DEFAULT_TOOL_OUTPUT_MAX_CHARS)


def truncate_tool_output(text: str, max_chars: Optional[int] = None) -> str:
    """Cut a tool result to max_chars and append an explicit truncation marker."""
    limit = get_tool_output_max_chars() if max_chars is None else max_chars
    if limit <= 0 or len(text) <= limit:
        return text
    return (
        text[:limit]
        + f"\n...[truncated: {len(text) - limit} of {len(text)} characters removed "
        f"(TOOL_OUTPUT_MAX_CHARS={limit})]"
    )


def truncate_tool_call_output(request: Any, execute: Any) -> Any:
    """ToolNode wrapper (wrap_tool_call): run the tool, then truncate its result."""
    result = execute(request)
    if isinstance(result, ToolMessage) and isinstance(result.content, str):
        truncated = truncate_tool_output(result.content)
        if truncated != result.content:
            logger.info(
                "Tool %s output truncated from %d to %d characters",
                result.name, len(result.content), len(truncated),
            )
            result = result.model_copy(update={"content": truncated})
    return result


def current_run_messages(messages: Sequence[BaseMessage]) -> List[BaseMessage]:
    """Messages of the current diagnosis run: from the last HumanMessage to the end."""
    messages = list(messages or [])
    for index in range(len(messages) - 1, -1, -1):
        if isinstance(messages[index], HumanMessage):
            return messages[index:]
    return messages


def tools_called(messages: Sequence[BaseMessage]) -> List[str]:
    """Names of the tools executed during the current diagnosis run."""
    return [
        message.name or "unknown"
        for message in current_run_messages(messages)
        if isinstance(message, ToolMessage)
    ]


def step_limit_reached(messages: Sequence[BaseMessage]) -> bool:
    """True if the last tool call of the run was never executed (step limit reached)."""
    run = current_run_messages(messages)
    for index in range(len(run) - 1, -1, -1):
        message = run[index]
        if isinstance(message, AIMessage) and message.tool_calls:
            return not any(isinstance(m, ToolMessage) for m in run[index + 1:])
    return False


def invoke_diagnosis(
    agent: Any, graph_input: Any, config: Optional[Dict[str, Any]] = None
) -> Tuple[Dict[str, Any], Optional[str]]:
    """Invoke the diagnostic graph with the recursion limit.

    Returns (final_state, degraded_reason). degraded_reason is None on a normal
    run and "recursion_limit" when the agent reached AGENT_RECURSION_LIMIT:
    - usually the router stopped the investigation early and final_result holds
      a partial diagnosis built from the data collected so far;
    - if LangGraph raised GraphRecursionError, the state is the one reached at
      the last completed step and there is no final_result.
    """
    run_config = {**(config or {}), "recursion_limit": get_recursion_limit()}
    state: Dict[str, Any] = {}
    try:
        # Same result as agent.invoke(), but keeps the latest state if the run is stopped.
        for state in agent.stream(graph_input, config=run_config, stream_mode="values"):
            pass
        state = dict(state)
        if step_limit_reached(state.get("messages", [])):
            logger.warning("Diagnosis finalized early: step limit reached (AGENT_RECURSION_LIMIT=%s)",
                           run_config["recursion_limit"])
            return state, "recursion_limit"
        return state, None
    except GraphRecursionError:
        logger.warning(
            "Diagnosis stopped: recursion limit reached (AGENT_RECURSION_LIMIT=%s)",
            run_config["recursion_limit"],
        )
        return {**dict(state), "final_result": None}, "recursion_limit"


def degraded_diagnosis_message(state: Dict[str, Any]) -> str:
    """Explicit text returned when the step limit (AGENT_RECURSION_LIMIT) is reached."""
    called = tools_called(state.get("messages", []))
    tools_text = ", ".join(called) if called else "none recorded"
    header = (
        f"Partial diagnosis: the agent reached the step limit (AGENT_RECURSION_LIMIT={get_recursion_limit()}) "
        f"and stopped the investigation early. Tools called: {tools_text}."
    )
    partial = state.get("final_result")
    if partial:
        return f"{header}\n\n{partial}"
    return (
        f"{header} No final diagnosis was produced. "
        "Retry the diagnosis, or raise AGENT_RECURSION_LIMIT if the investigation needs more steps."
    )
