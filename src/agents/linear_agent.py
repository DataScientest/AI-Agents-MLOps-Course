# src/agents/linear_agent.py
import logging
from typing import List
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import Tool
from langgraph.graph import StateGraph, START, END

from src.state import AgentState
from tools.mlops_tools import get_system_metrics # Import the tool function directly

logger = logging.getLogger(__name__)

# --- Pattern 1 : Linear Workflow (Basic Health Report Agent) ---
# Objective: Collect CPU metrics, generate a simple report.
def create_linear_report_agent(llm_client: ChatGroq, tools_for_graph: List[Tool]):
    workflow = StateGraph(AgentState)

    # Node 1: Fetch CPU metrics
    def get_cpu_metrics_node(state: AgentState):
        logger.info("Node 'get_cpu_metrics' : Fetching CPU metrics.")
        metrics = get_system_metrics("CPU") # Call our tool function directly
        return {"messages": [AIMessage(content=f"CPU metrics retrieved: {metrics}")], "system_metrics": {"CPU": metrics}}

    # Node 2: Generate report (LLM)
    def generate_report_node(state: AgentState):
        logger.info("Node 'generate_report' : Generating health report.")
        cpu_metrics_str = state["system_metrics"].get("CPU", "unavailable")
        report_prompt = ChatPromptTemplate.from_messages([
            SystemMessage("You are a system health report agent. Generate a concise report based on the provided metrics."),
            HumanMessage(f"Here are the CPU metrics: {cpu_metrics_str}. Write a brief health report.")
        ])
        # Invoke LLM with messages
        response = llm_client.invoke(report_prompt.format_messages())
        return {"messages": [AIMessage(content=f"Report generated: {response.content}")], "report_content": response.content}
    
    # Node 3: Finalize report (can just prepare the final message for the user)
    def finalize_report_node(state: AgentState):
        logger.info("Node 'finalize_report': Report finalized.")
        # Report content is already in state['report_content']
        # We just prepare the final message for "final_result" or the last message
        final_message = f"CPU health report completed. Content: {state['report_content']}"
        return {"messages": [AIMessage(content=final_message)], "final_result": final_message}

    workflow.add_node("get_cpu_metrics", get_cpu_metrics_node)
    workflow.add_node("generate_report", generate_report_node)
    workflow.add_node("finalize_report", finalize_report_node)

    workflow.set_entry_point("get_cpu_metrics")
    workflow.add_edge("get_cpu_metrics", "generate_report")
    workflow.add_edge("generate_report", "finalize_report")
    workflow.set_finish_point("finalize_report") # The graph ends after this node

    return workflow.compile()
