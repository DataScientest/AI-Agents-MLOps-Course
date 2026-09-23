from typing import List, Annotated, Any, Literal, Optional
from typing_extensions import TypedDict

from langchain_core.messages import BaseMessage
from langgraph.managed import RemainingSteps

def add_messages(left: List[BaseMessage], right: List[BaseMessage]) -> List[BaseMessage]:
    """Adds messages to the graph state, used to manage conversation history."""
    return left + right

class AgentState(TypedDict):
    """
    Represents the shared state of the agent graph.
    Each key can be updated by the nodes.
    """
    messages: Annotated[List[BaseMessage], add_messages] 
    # Managed by LangGraph (not stored): steps left before AGENT_RECURSION_LIMIT
    remaining_steps: RemainingSteps

    alert_info: str
    alert_severity: Literal["critical", "medium", "low", "unknown"]

    prometheus_data: str
    loki_logs: str
    grafana_link: str
    
    final_result: Any