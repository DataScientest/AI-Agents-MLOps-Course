# src/agents/human_in_loop_agent.py
import logging
from typing import List
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import Tool
from langgraph.graph import END, START, StateGraph

from src.nodes.human_in_loop_agent import (
    apply_action_node,
    build_propose_action_node,
    feedback_decision_node,
    reject_action_node,
    route_entry,
    route_on_feedback,
)
from src.state import AgentState

logger = logging.getLogger(__name__)

# --- Pattern 4 : Human-in-the-Loop (Fix Approval Agent) ---
def create_human_in_loop_agent(llm_client: BaseChatModel, tools_for_graph: List[Tool]):
    workflow = StateGraph(AgentState)

    propose_action_node = build_propose_action_node(llm_client)

    workflow.add_node("propose_action", propose_action_node)
    workflow.add_node("feedback_decision_node", feedback_decision_node)
    workflow.add_node("apply_action", apply_action_node)
    workflow.add_node("reject_action", reject_action_node)

    # Entry routing: the first invoke proposes an action; the second invoke (state already
    # holds proposed_action and human_feedback) resumes directly at the decision point,
    # so the approved action is exactly the one that was proposed.
    workflow.add_conditional_edges(
        START,
        route_entry,
        {
            "propose_action": "propose_action",
            "feedback_decision_node": "feedback_decision_node",
        }
    )
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
