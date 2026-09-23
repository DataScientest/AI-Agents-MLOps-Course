"""LangGraph node that summarises the investigation into a final diagnosis."""

from __future__ import annotations

import logging
from typing import Dict, List

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate

from guardrails import current_run_messages, truncate_tool_output
from nodes.llm import LLMRateLimitError, rate_limit_status
from state import AgentState

logger = logging.getLogger(__name__)

# Tool name -> state field that stores its results for the summary prompt.
TOOL_RESULT_FIELDS = {
    "PrometheusQuery": "prometheus_data",
    "LokiLogSearch": "loki_logs",
    "GrafanaDashboardLink": "grafana_link",
}


def collect_tool_results(state: AgentState) -> Dict[str, str]:
    """Group the tool results (ToolMessage contents) of the current run for the summary prompt."""
    grouped: Dict[str, List[str]] = {field: [] for field in TOOL_RESULT_FIELDS.values()}
    other: List[str] = []
    notes = ""
    for message in current_run_messages(state.get("messages", [])):
        if isinstance(message, ToolMessage):
            content = truncate_tool_output(str(message.content))
            field = TOOL_RESULT_FIELDS.get(message.name or "")
            if field:
                grouped[field].append(content)
            else:
                other.append(f"[{message.name}] {content}")
        elif isinstance(message, AIMessage) and not message.tool_calls and message.content:
            notes = str(message.content)
    return {
        "prometheus_data": "\n\n".join(grouped["prometheus_data"]) or state.get("prometheus_data") or "No data.",
        "loki_logs": "\n\n".join(grouped["loki_logs"]) or state.get("loki_logs") or "No logs.",
        "grafana_link": "\n".join(grouped["grafana_link"]) or state.get("grafana_link") or "No link generated.",
        "other_tool_results": "\n\n".join(other) or "None.",
        "investigation_notes": truncate_tool_output(notes) or "None.",
    }


def finalize_diagnosis_node(
    *,
    llm: BaseChatModel,
    system_prompt: str,
    human_template: str,
):
    """Return a callable that produces the final diagnosis narrative."""

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", human_template),
        ]
    )

    def _node(state: AgentState) -> AgentState:
        logger.info("Node 'finalize_diagnosis': summarising alert %s", state.get("alert_info"))
        results = collect_tool_results(state)
        rendered_messages = prompt.format_messages(alert_info=state.get("alert_info", ""), **results)
        try:
            final_response = llm.invoke(rendered_messages)
        except Exception as e:
            status = rate_limit_status(e)
            if status is not None:
                logger.error("LLM rate limited (provider HTTP %s): %s", status, e)
                raise LLMRateLimitError(
                    f"LLM rate limited (provider HTTP {status}): {e}", provider_status=status
                ) from e
            raise
        final_msg = final_response.content if hasattr(final_response, "content") else str(final_response)
        logger.info("Final diagnosis produced (usage: %s)", getattr(final_response, "usage_metadata", None))
        # The messages reducer appends: return only the new message, not the whole history.
        return {
            "messages": [AIMessage(content=final_msg)],
            "final_result": final_msg,
            "prometheus_data": results["prometheus_data"],
            "loki_logs": results["loki_logs"],
            "grafana_link": results["grafana_link"],
        }

    return _node
