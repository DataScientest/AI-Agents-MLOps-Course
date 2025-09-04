import logging
from typing import List, Literal

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.tools import Tool
from langgraph.graph import StateGraph, START, END

from state import AgentState
from tools.mlops_tools import check_alert_severity

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
        return {"alert_severity": severity, "messages": state['messages'] + [AIMessage(content=f"Alert evaluated. Severity: {severity}.")]}

    # Node 2a: Handle critical alert
    def handle_critical_alert_node(state: AgentState):
        logger.info(f"Node 'handle_critical_alert': Critical alert ({state['alert_info']}). Immediate escalation.")
        final_msg = "CRITICAL alert detected. Immediate escalation to on-call pager."
        return {"messages": state['messages'] + [AIMessage(content=final_msg)], "final_result": final_msg}

    # Node 2b: Handle medium alert
    def handle_medium_alert_node(state: AgentState):
        logger.info(f"Nœud 'handle_medium_alert': Alerte modérée ({state['alert_info']}). Lancement diagnostic auto.")
        final_msg = "MEDIUM alert detected. Starting automatic diagnosis."
        return {"messages": state['messages'] + [AIMessage(content=final_msg)], "final_result": final_msg}

    # Nœud 2c : Handle low alert
    def handle_low_alert_node(state: AgentState):
        logger.info(f"Nœud 'handle_low_alert': Alerte faible ({state['alert_info']}). Archivage simple.")
        final_msg = "LOW alert detected. Archiving for later analysis."
        return {"messages": state['messages'] + [AIMessage(content=final_msg)], "final_result": final_msg}
    
    def route_alert(state: AgentState) -> str:
        severity = state["alert_severity"]
        if severity == "critical":
            return "handle_critical"
        elif severity == "medium":
            return "handle_medium"
        else:
            return "handle_low"

    workflow.add_node("evaluate_alert", evaluate_alert_node)
    workflow.add_node("handle_critical", handle_critical_alert_node)
    workflow.add_node("handle_medium", handle_medium_alert_node)
    workflow.add_node("handle_low", handle_low_alert_node)

    workflow.set_entry_point("evaluate_alert")
    workflow.add_conditional_edges(
        "evaluate_alert",
        route_alert,
        {
            "handle_critical": "handle_critical",
            "handle_medium": "handle_medium",
            "handle_low": "handle_low",
        },
    )

    workflow.set_finish_point("handle_critical")
    workflow.set_finish_point("handle_medium")
    workflow.set_finish_point("handle_low")

    return workflow.compile()