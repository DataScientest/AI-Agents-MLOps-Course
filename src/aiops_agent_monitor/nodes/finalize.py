"""LangGraph node that summarises the investigation into a final diagnosis."""

from __future__ import annotations

import logging

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate

from state import AgentState

logger = logging.getLogger(__name__)


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
        rendered_messages = prompt.format_messages(
            alert_info=state.get("alert_info", ""),
            prometheus_data=state.get("prometheus_data", "No data."),
            loki_logs=state.get("loki_logs", "No logs."),
            grafana_link=state.get("grafana_link", "No link generated."),
        )
        final_response = llm.invoke(rendered_messages)
        final_msg = final_response.content if hasattr(final_response, "content") else str(final_response)
        return {
            "messages": state["messages"] + [AIMessage(content=final_msg)],
            "final_result": final_msg,
        }

    return _node
