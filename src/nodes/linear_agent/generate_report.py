import logging

from langchain_groq import ChatGroq
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from src.state import AgentState

logger = logging.getLogger(__name__)


def build_generate_report_node(llm_client: ChatGroq):
    def generate_report_node(state: AgentState):
        logger.info("Node 'generate_report' : Generating health report.")
        cpu_metrics_str = state["system_metrics"].get("CPU", "unavailable")
        report_prompt = ChatPromptTemplate.from_messages([
            SystemMessage("You are a system health report agent. Generate a concise report based on the provided metrics."),
            HumanMessage(f"Here are the CPU metrics: {cpu_metrics_str}. Write a brief health report."),
        ])
        response = llm_client.invoke(report_prompt.format_messages())
        return {
            "messages": [AIMessage(content=f"Report generated: {response.content}")],
            "report_content": response.content,
        }

    return generate_report_node
