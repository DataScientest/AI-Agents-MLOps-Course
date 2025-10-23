import logging

from langchain_core.messages import AIMessage

from src.state import AgentState

logger = logging.getLogger(__name__)


def handle_medium_alert_node(state: AgentState):
    logger.info(f"Node 'handle_medium_alert': Medium alert ({state['alert_info']}). Launching auto-diagnosis.")
    final_msg = "MEDIUM alert detected. Starting automatic diagnosis."
    return {"messages": [AIMessage(content=final_msg)], "final_result": final_msg}
