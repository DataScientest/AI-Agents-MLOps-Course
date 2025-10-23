import logging

from src.state import AgentState

logger = logging.getLogger(__name__)


def feedback_decision_node(state: AgentState):
    logger.info(
        "Node 'feedback_decision_node': Graph has reached decision point for human feedback. "
        f"Current human_feedback: {state.get('human_feedback')}"
    )
    return state
