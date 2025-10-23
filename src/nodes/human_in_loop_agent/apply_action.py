import logging

from langchain_core.messages import AIMessage

from src.state import AgentState
from src.tools.mlops_tools import apply_fix

logger = logging.getLogger(__name__)


def apply_action_node(state: AgentState):
    logger.info(
        f"Node 'apply_action': Applying approved action: '{state['proposed_action']}'"
    )
    result = apply_fix(state["proposed_action"])
    final_msg = f"Action applied: {result}"

    return {
        "messages": state["messages"] + [AIMessage(content=final_msg)],
        "final_result": final_msg,
    }
