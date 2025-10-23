import logging

from langchain_core.messages import AIMessage

from src.state import AgentState

logger = logging.getLogger(__name__)


def finalize_report_node(state: AgentState):
    logger.info("Node 'finalize_report': Report finalized.")
    final_message = f"CPU health report completed. Content: {state['report_content']}"
    return {
        "messages": [AIMessage(content=final_message)],
        "final_result": final_message,
    }
