"""LangGraph node responsible for LLM + tool orchestration."""

from __future__ import annotations

import logging
from typing import Iterable

from langchain_core.messages import BaseMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import BaseTool
from langchain_core.language_models import BaseChatModel

from state import AgentState

logger = logging.getLogger(__name__)


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
        result: BaseMessage = llm_chain.invoke({"messages": state["messages"]})
        logger.info("LLM produced result: %s", result)
        return {"messages": [result]}

    return _node
