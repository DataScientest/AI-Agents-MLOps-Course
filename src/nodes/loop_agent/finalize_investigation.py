import logging

from langchain_core.messages import AIMessage

from src.state import AgentState

logger = logging.getLogger(__name__)


def finalize_investigation_node(state: AgentState):
    logger.info("Node 'finalize_investigation': Finalizing investigation.")
    if state["logs_found"]:
        final_msg = "Investigation completed: Relevant logs found."
    else:
        final_msg = (
            f"Investigation completed: No logs found after {state['investigation_step']} attempts."
        )
    return {
        "messages": state["messages"] + [AIMessage(content=final_msg)],
        "final_result": final_msg,
    }
