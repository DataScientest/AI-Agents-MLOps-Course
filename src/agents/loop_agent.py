import logging

from typing import List
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import Tool
from langgraph.graph import StateGraph

from src.nodes.loop_agent import (
    build_search_logs_node,
    continue_investigation,
    finalize_investigation_node,
    initialize_investigation_node,
)
from src.state import AgentState

logger = logging.getLogger(__name__)

# --- Pattern 3 : Loop with Conditions (Log Investigation Agent) ---
def create_log_investigator_agent(llm_client: BaseChatModel, tools_for_graph: List[Tool]):
    workflow = StateGraph(AgentState)

    search_logs_node = build_search_logs_node(llm_client)

    workflow.add_node("initialize_investigation", initialize_investigation_node)
    workflow.add_node("search_logs_node", search_logs_node)
    workflow.add_node("finalize_investigation", finalize_investigation_node)

    workflow.set_entry_point("initialize_investigation")
    workflow.add_edge("initialize_investigation", "search_logs_node") # First search after init
    
    # Here, the loop: from 'search_logs_node' to 'search_logs_node' (loop) or to 'finalize_investigation' (exit)
    workflow.add_conditional_edges(
        "search_logs_node",
        continue_investigation,
        {
            "search_logs_node": "search_logs_node",      # Loop on search
            "end_investigation": "finalize_investigation" # Exit loop
        }
    )
    workflow.set_finish_point("finalize_investigation")

    return workflow.compile()
