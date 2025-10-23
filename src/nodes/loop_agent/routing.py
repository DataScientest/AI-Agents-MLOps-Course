import logging

from src.state import AgentState

logger = logging.getLogger(__name__)


def continue_investigation(state: AgentState) -> str:
    logger.info(
        "Routing function 'continue_investigation' called. Current state: logs_found=%s, investigation_step=%s",
        state["logs_found"],
        state["investigation_step"],
    )
    if state["logs_found"]:
        logger.info("Loop condition: Logs found, exiting.")
        return "end_investigation"
    if state["investigation_step"] >= state["max_investigation_steps"]:
        logger.info("Loop condition: Max attempts reached, exiting.")
        return "end_investigation"
    logger.info(
        "Loop condition: Continuing investigation (step %s/%s).",
        state["investigation_step"],
        state["max_investigation_steps"],
    )
    return "search_logs_node"
