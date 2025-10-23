import logging

from langchain_core.messages import AIMessage

from src.state import AgentState

logger = logging.getLogger(__name__)


def handle_critical_alert_node(state: AgentState):
    logger.info(f"Node 'handle_critical_alert': Critical alert ({state['alert_info']}). Immediate escalation.")
    final_msg = "CRITICAL alert detected. Immediate escalation to on-call pager."
    return {"messages": [AIMessage(content=final_msg)], "final_result": final_msg}
