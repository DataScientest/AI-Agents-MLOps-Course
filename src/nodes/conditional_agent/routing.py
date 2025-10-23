import logging

from src.state import AgentState

logger = logging.getLogger(__name__)


def route_alert(state: AgentState) -> str:
    severity = state["alert_severity"]
    logger.info("Routing alert based on severity: %s", severity)
    if severity == "critical":
        return "handle_critical"
    elif severity == "medium":
        return "handle_medium"
    else:
        return "handle_low"
