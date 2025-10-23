# src/agents/human_in_loop_agent.py
import logging
from typing import List
from langchain_groq import ChatGroq
from langchain_core.tools import Tool
from langgraph.graph import END, StateGraph

from src.nodes.human_in_loop_agent import (
    apply_action_node,
    build_propose_action_node,
    feedback_decision_node,
    reject_action_node,
    route_on_feedback,
)
from src.state import AgentState

logger = logging.getLogger(__name__)

# --- Pattern 4 : Human-in-the-Loop (Fix Approval Agent) ---
def create_human_in_loop_agent(llm_client: ChatGroq, tools_for_graph: List[Tool]):
    workflow = StateGraph(AgentState)

    propose_action_node = build_propose_action_node(llm_client)

    workflow.add_node("propose_action", propose_action_node)
    workflow.add_node("feedback_decision_node", feedback_decision_node)
    workflow.add_node("apply_action", apply_action_node)
    workflow.add_node("reject_action", reject_action_node)

    workflow.set_entry_point("propose_action")
    workflow.add_edge("propose_action", "feedback_decision_node")

    workflow.add_conditional_edges(
        "feedback_decision_node",
        route_on_feedback,
        {
            "apply_action": "apply_action",
            "reject_action": "reject_action",
            "await_and_end": END 
        }
    )

    workflow.set_finish_point("apply_action")
    workflow.set_finish_point("reject_action")

    return workflow.compile()
