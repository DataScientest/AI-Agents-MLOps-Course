import logging

from langchain_core.messages import AIMessage

from src.state import AgentState
from src.tools.mlops_tools import get_system_metrics

logger = logging.getLogger(__name__)


def get_cpu_metrics_node(state: AgentState):
    logger.info("Node 'get_cpu_metrics' : Fetching CPU metrics.")
    metrics = get_system_metrics("CPU")
    return {
        "messages": [AIMessage(content=f"CPU metrics retrieved: {metrics}")],
        "system_metrics": {"CPU": metrics},
    }
