import logging

from typing import List
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import Tool
from langgraph.graph import StateGraph

from src.nodes.conditional_agent import (
    evaluate_alert_node,
    handle_critical_alert_node,
    handle_low_alert_node,
    handle_medium_alert_node,
    route_alert,
)
from src.state import AgentState

logger = logging.getLogger(__name__)

# --- Pattern 2 : Conditional Branching (Alert Routing Agent) ---
# Objective: Route an alert based on its severity (critical, medium, low).
def create_alert_router_agent(llm_client: BaseChatModel, tools_for_graph: List[Tool]):
    workflow = StateGraph(AgentState)

    workflow.add_node("evaluate_alert", evaluate_alert_node)
    workflow.add_node("handle_critical", handle_critical_alert_node)
    workflow.add_node("handle_medium", handle_medium_alert_node)
    workflow.add_node("handle_low", handle_low_alert_node)

    workflow.set_entry_point("evaluate_alert")
    workflow.add_conditional_edges(
        "evaluate_alert", # Node from which the branch starts
        route_alert,      # Function that decides the destination
        {                 # Mapping of function outputs to node names
            "handle_critical": "handle_critical",
            "handle_medium": "handle_medium",
            "handle_low": "handle_low",
        },
    )
    # All branches lead to an end, so all are finish points
    workflow.set_finish_point("handle_critical")
    workflow.set_finish_point("handle_medium")
    workflow.set_finish_point("handle_low")

    return workflow.compile()
