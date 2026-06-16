"""LangGraph diagnostic agent factory with PostgreSQL checkpointing support."""

from __future__ import annotations

import logging
from typing import Iterable, Optional

from langchain_core.tools import BaseTool
from langchain_core.language_models import BaseChatModel
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.postgres import PostgresSaver

from prompts import (
    DIAGNOSTIC_SYSTEM_PROMPT,
    FINAL_SUMMARY_SYSTEM_PROMPT,
    FINAL_SUMMARY_HUMAN_TEMPLATE,
)
from state import AgentState
from nodes.llm import llm_agent_node
from nodes.finalize import finalize_diagnosis_node
from nodes.routing import route_agent_decide

logger = logging.getLogger(__name__)


def build_diagnostic_agent(
    llm: BaseChatModel,
    tools: Iterable[BaseTool],
    checkpointer: Optional[PostgresSaver] = None
) -> StateGraph:
    """Create the compiled diagnostic agent graph with optional PostgreSQL checkpointing.
    
    Args:
        llm: The ChatGroq LLM instance
        tools: Iterable of LangChain tools for the agent
        checkpointer: Optional PostgresSaver for persistent memory
        
    Returns:
        Compiled StateGraph with optional checkpointing
    """
    graph = StateGraph(AgentState)
    graph.add_node("llm_agent_node", llm_agent_node(llm, tools, DIAGNOSTIC_SYSTEM_PROMPT))
    graph.add_node("tool_executor", ToolNode(tools))
    graph.add_node(
        "finalize_diagnosis",
        finalize_diagnosis_node(
            llm=llm,
            system_prompt=FINAL_SUMMARY_SYSTEM_PROMPT,
            human_template=FINAL_SUMMARY_HUMAN_TEMPLATE,
        ),
    )

    graph.set_entry_point("llm_agent_node")
    graph.add_conditional_edges(
        "llm_agent_node",
        route_agent_decide,
        {
            "tool_executor": "tool_executor",
            "finalize_diagnosis": "finalize_diagnosis",
        },
    )
    graph.add_edge("tool_executor", "llm_agent_node")
    graph.set_finish_point("finalize_diagnosis")

    if checkpointer:
        logger.info("Diagnostic agent graph configured with PostgreSQL checkpointing.")
    else:
        logger.info("Diagnostic agent graph configured without checkpointing.")
    
    return graph.compile(checkpointer=checkpointer)
