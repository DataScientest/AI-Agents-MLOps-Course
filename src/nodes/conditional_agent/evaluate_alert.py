import logging

from langchain_core.messages import AIMessage

from src.state import AgentState
from src.tools.mlops_tools import check_alert_severity

logger = logging.getLogger(__name__)


def evaluate_alert_node(state: AgentState):
    logger.info(f"Node 'evaluate_alert': Evaluating alert: {state['alert_info']}")
    severity = check_alert_severity(state["alert_info"])
    logger.info(f"Detected alert severity: {severity}")
    return {
        "alert_severity": severity,
        "messages": [AIMessage(content=f"Alert evaluated. Severity: {severity}.")],
    }
