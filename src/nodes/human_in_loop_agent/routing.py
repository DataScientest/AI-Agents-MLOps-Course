import logging

from src.state import AgentState

logger = logging.getLogger(__name__)


def route_on_feedback(state: AgentState) -> str:
    logger.info(
        "Routing function 'route_on_feedback' : human_feedback=%s",
        state.get("human_feedback"),
    )
    if state.get("human_feedback") == "approved":
        logger.info("Human feedback: Approved. Routing to apply_action.")
        return "apply_action"
    elif state.get("human_feedback") == "rejected":
        logger.info("Human feedback: Rejected. Routing to reject_action.")
        return "reject_action"
    else:
        logger.info(
            "No human feedback received yet. Routing to 'await_and_end' to pause current invoke and await external update."
        )
        return "await_and_end"
