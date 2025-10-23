import logging

from langchain_groq import ChatGroq
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from src.state import AgentState

logger = logging.getLogger(__name__)


def build_propose_action_node(llm_client: ChatGroq):
    def propose_action_node(state: AgentState):
        logger.info("Node 'propose_action': Action proposal.")

        original_problem_message_content = "Problem not specified."
        for msg in state["messages"]:
            if isinstance(msg, HumanMessage) and msg.content and not msg.content.startswith(
                "Human intervention required:"
            ):
                original_problem_message_content = msg.content
                break
        problem_description = original_problem_message_content

        llm_prompt = ChatPromptTemplate.from_messages([
            SystemMessage(
                "You are a problem analysis agent. Your task is to propose a simple and safe corrective action "
                "for the problem described. The action should be DIRECTLY APPLICABLE, like 'Restart service X' or 'Deploy config Y'. "
                "Be concise and propose ONLY ONE CONCRETE action, not a question or a general statement."
            ),
            HumanMessage(
                f"Problem: {problem_description}. What CONCRETE corrective action do you propose?"
            ),
        ])
        llm_response = llm_client.invoke(llm_prompt.format_messages()).content

        return {
            "proposed_action": llm_response.strip(),
            "messages": state["messages"]
            + [
                AIMessage(
                    content=f"Proposed action: '{llm_response.strip()}'. Awaiting human approval."
                ),
                HumanMessage(
                    content="Human intervention required: Please provide feedback ('approved' or 'rejected') via 'human_feedback' state update."
                ),
            ],
        }

    return propose_action_node
