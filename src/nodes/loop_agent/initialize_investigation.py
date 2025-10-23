import logging

from langchain_core.messages import AIMessage

from src.state import AgentState

logger = logging.getLogger(__name__)


def initialize_investigation_node(state: AgentState):
    logger.info(
        f"Node 'initialize_investigation': Starting investigation for '{state['investigation_query']}'"
    )
    return {
        "investigation_step": 0,
        "logs_found": False,
        "messages": [
            AIMessage(content=f"Starting investigation for: {state['investigation_query']}")
        ],
    }
