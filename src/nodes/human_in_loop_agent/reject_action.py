import logging

from langchain_core.messages import AIMessage

from src.state import AgentState

logger = logging.getLogger(__name__)


def reject_action_node(state: AgentState):
    logger.info("Node 'reject_action': Action rejected by human.")
    final_msg = f"Action rejected by human. Feedback: {state['human_feedback']}. End."

    return {
        "messages": state["messages"] + [AIMessage(content=final_msg)],
        "final_result": final_msg,
    }
