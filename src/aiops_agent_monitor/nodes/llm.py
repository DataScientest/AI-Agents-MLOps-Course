"""LangGraph node responsible for LLM + tool orchestration."""

from __future__ import annotations

import logging
import time
from typing import Iterable

from langchain_core.messages import BaseMessage, SystemMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import BaseTool
from langchain_groq import ChatGroq
import groq

from state import AgentState

logger = logging.getLogger(__name__)


def llm_agent_node(
    llm: ChatGroq,
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
        try:
            result: BaseMessage = llm_chain.invoke({"messages": state["messages"]})
            logger.info("LLM produced result: %s", result)
            return {"messages": [result]}
        except Exception as e:
            # Handle GROQ Rate Limits (429) gracefully by returning a helpful message
            # rather than crashing the entire workflow with a 500 error.
            if "rate_limit_exceeded" in str(e).lower() or "429" in str(e):
                logger.error("GROQ Rate Limit Hit: %s", e)
                error_msg = AIMessage(content="I'm sorry, but I've reached my daily limit for analyzing alerts. Please try again later when my quota resets.")
                return {"messages": [error_msg]}
            
            logger.error("Error in llm_agent_node: %s", e)
            raise e

    return _node
