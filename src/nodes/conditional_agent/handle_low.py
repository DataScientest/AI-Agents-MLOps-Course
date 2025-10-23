import logging

from langchain_core.messages import AIMessage

from src.state import AgentState

logger = logging.getLogger(__name__)


def handle_low_alert_node(state: AgentState):
    logger.info(f"Node 'handle_low_alert': Low alert ({state['alert_info']}). Simple archiving.")
    final_msg = "LOW alert detected. Archiving for later analysis."
    return {"messages": [AIMessage(content=final_msg)], "final_result": final_msg}
