from typing import List, Annotated, Any, Literal, Optional
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage

def add_messages(left: List[BaseMessage], right: List[BaseMessage]) -> List[BaseMessage]:
    """Adds messages to the graph state, used to manage conversation history."""
    return left + right

class AgentState(TypedDict):
    """
    Represents the shared state of the agent graph.
    Each key can be updated by the nodes.
    """
    messages: Annotated[List[BaseMessage], add_messages]

    alert_info: str
    alert_severity: Literal["critical", "medium", "low", "unknown"]

    prometheus_data: str
    loki_logs: str
    grafana_link: str

    # Chapter 4 - Part 2: RAG knowledge retrieval
    rag_similar_incidents: Optional[str]  # Formatted similar incidents from KB
    historical_context_used: bool  # Whether RAG was consulted

    # Chapter 4 - Part 3: Learning and confidence
    diagnosis_id: Optional[str]  # Unique ID for this diagnosis
    confidence_score: Optional[float]  # Confidence in diagnosis (0.0-1.0)
    recommended_action: Literal["auto_remediate", "suggest", "escalate", "unknown"]

    thread_id: Optional[str]
    proposed_action: Optional[str]
    human_feedback: Optional[str]

    final_result: Any