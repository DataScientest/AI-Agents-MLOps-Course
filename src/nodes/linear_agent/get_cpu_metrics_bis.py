import logging

from langchain_core.messages import AIMessage

from src.state import AgentState
from src.tools.mlops_tools import get_system_metrics

logger = logging.getLogger(__name__)

# Update
def get_cpu_metrics_node(state: AgentState):
    logger.info("Node 'get_cpu_metrics' : Fetching CPU and Memory metrics.")
    cpu = get_system_metrics("CPU")
    memory = get_system_metrics("Memory") # Fetch memory metrics

    return {
        "messages": [AIMessage(content=f"Metrics retrieved: CPU={cpu}, Memory={memory}")],
        "system_metrics": {
            "CPU": cpu,
            "Memory": memory, # Add memory metrics to state
        },
    }