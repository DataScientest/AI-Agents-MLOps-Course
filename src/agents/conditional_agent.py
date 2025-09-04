import logging

from typing import List, Literal
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.tools import Tool
from langgraph.graph import StateGraph, START, END

from src.state import AgentState
from tools.mlops_tools import check_alert_severity # Import the tool function directly

logger = logging.getLogger(__name__)

# --- Pattern 2 : Conditional Branching (Alert Routing Agent) ---
# Objective: Route an alert based on its severity (critical, medium, low).
def create_alert_router_agent(llm_client: ChatGroq, tools_for_graph: List[Tool]):
    workflow = StateGraph(AgentState)

    # Node 1: Evaluate alert severity
    def evaluate_alert_node(state: AgentState):
        logger.info(f"Node 'evaluate_alert': Evaluating alert: {state['alert_info']}")
        severity = check_alert_severity(state["alert_info"]) # Direct tool usage
        logger.info(f"Detected alert severity: {severity}")
        return {"alert_severity": severity, "messages": [AIMessage(content=f"Alert evaluated. Severity: {severity}.")]}

    # Node 2a: Handle critical alert
    def handle_critical_alert_node(state: AgentState):
        logger.info(f"Node 'handle_critical_alert': Critical alert ({state['alert_info']}). Immediate escalation.")
        final_msg = "CRITICAL alert detected. Immediate escalation to on-call pager."
        return {"messages": [AIMessage(content=final_msg)], "final_result": final_msg}

    # Node 2b: Handle medium alert
    def handle_medium_alert_node(state: AgentState):
        logger.info(f"Node 'handle_medium_alert': Medium alert ({state['alert_info']}). Launching auto-diagnosis.")
        final_msg = "MEDIUM alert detected. Starting automatic diagnosis."
        return {"messages": [AIMessage(content=final_msg)], "final_result": final_msg}

    # Node 2c: Handle low alert
    def handle_low_alert_node(state: AgentState):
        logger.info(f"Node 'handle_low_alert': Low alert ({state['alert_info']}). Simple archiving.")
        final_msg = "LOW alert detected. Archiving for later analysis."
        return {"messages": [AIMessage(content=final_msg)], "final_result": final_msg}
    
    # Conditional routing function that determines the next step
    def route_alert(state: AgentState) -> str:
        severity = state["alert_severity"]
        if severity == "critical":
            return "handle_critical"
        elif severity == "medium":
            return "handle_medium"
        else: # "low" or "unknown"
            return "handle_low"

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
