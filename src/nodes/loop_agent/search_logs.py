import logging

from langchain_groq import ChatGroq
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from src.state import AgentState
from src.tools.mlops_tools import search_logs

logger = logging.getLogger(__name__)


def build_search_logs_node(llm_client: ChatGroq):
    def search_logs_node(state: AgentState):
        logger.info(
            f"Node 'search_logs': Search step {state['investigation_step']} for '{state['investigation_query']}'"
        )
        search_result = search_logs(state["investigation_query"])

        found = "log trouvé" in search_result.lower()
        updated_step = state["investigation_step"] + 1
        new_messages = state["messages"] + [
            AIMessage(content=f"Log search for '{state['investigation_query']}' : {search_result}")
        ]

        updates = {
            "messages": new_messages,
            "investigation_step": updated_step,
            "logs_found": found,
        }

        if not found and updated_step <= state["max_investigation_steps"]:
            llm_thought_prompt = ChatPromptTemplate.from_messages([
                SystemMessage(
                    "You are a log search expert. If a search yielded no results, propose a slight variation of the query for the next attempt. Be concise and give only the new query."
                ),
                HumanMessage(
                    f"Search for '{state['investigation_query']}' yielded no results. Propose a concise alternative query."
                ),
            ])
            llm_response_obj = llm_client.invoke(llm_thought_prompt.format_messages())
            new_query = llm_response_obj.content.strip()

            updates["investigation_query"] = new_query
            updates["messages"] = updates["messages"] + [
                AIMessage(content=f"LLM suggestion for next search: {new_query}")
            ]

        return updates

    return search_logs_node
