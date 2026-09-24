# src/agents/linear_agent.py
import logging
from typing import List
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import Tool
from langgraph.graph import StateGraph

from src.nodes.linear_agent import (
    build_generate_report_node,
    finalize_report_node,
    get_cpu_metrics_node,
)
from src.state import AgentState

logger = logging.getLogger(__name__)

# --- Pattern 1 : Linear Workflow (Basic Health Report Agent) ---
# Objective: Collect CPU metrics, generate a simple report.
def create_linear_report_agent(llm_client: BaseChatModel, tools_for_graph: List[Tool]):
    workflow = StateGraph(AgentState)

    generate_report_node = build_generate_report_node(llm_client)

    workflow.add_node("get_cpu_metrics", get_cpu_metrics_node)
    workflow.add_node("generate_report", generate_report_node)
    workflow.add_node("finalize_report", finalize_report_node)

    workflow.set_entry_point("get_cpu_metrics")
    workflow.add_edge("get_cpu_metrics", "generate_report")
    workflow.add_edge("generate_report", "finalize_report")
    workflow.set_finish_point("finalize_report") # The graph ends after this node

    return workflow.compile()
