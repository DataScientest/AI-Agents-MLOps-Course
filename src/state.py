# src/state.py
from typing import List, Annotated, Any, Literal
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

def add_messages(left: List[BaseMessage], right: List[BaseMessage]) -> List[BaseMessage]:
    """Adds messages to the graph state, used to manage conversation history."""
    # Ensure that if 'left' is None (which it shouldn't be with TypedDict), we handle it.
    # But with Annotated, it should always be a list.
    return left + right

class AgentState(TypedDict):
    """
    Represents the shared state of the agent graph.
    Each key can be updated by the nodes.
    """
    # Keep messages as non-Optional, relying on add_messages to always produce a list
    messages: Annotated[List[BaseMessage], add_messages] # <-- Revert to non-Optional

    # --- Specific fields for this exercise (will be used by different patterns) ---
    alert_info: str
    alert_severity: Literal["critical", "medium", "low", "unknown"]
    
    investigation_query: str
    investigation_step: int
    max_investigation_steps: int
    logs_found: bool
    
    proposed_action: str
    human_approval_needed: bool
    human_feedback: str 
    
    system_metrics: dict
    report_content: str
    
    final_result: Any
