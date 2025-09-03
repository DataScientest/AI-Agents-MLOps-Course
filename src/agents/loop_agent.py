import logging

from typing import List
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import Tool
from langgraph.graph import StateGraph, START, END

from src.state import AgentState
from tools.mlops_tools import search_logs # Import the tool function directly

logger = logging.getLogger(__name__)

# --- Pattern 3 : Loop with Conditions (Log Investigation Agent) ---
def create_log_investigator_agent(llm_client: ChatGroq, tools_for_graph: List[Tool]):
    workflow = StateGraph(AgentState)
    
    # Nœud 1: Initialiser l'investigation
    def initialize_investigation_node(state: AgentState):
        logger.info(f"Node 'initialize_investigation': Starting investigation for '{state['investigation_query']}'")
        return {"investigation_step": 0, "logs_found": False, "messages": [AIMessage(content=f"Starting investigation for: {state['investigation_query']}")]}

    # Nœud 2: Rechercher dans les logs (utilise l'outil SearchLogs)
    def search_logs_node(state: AgentState):
        logger.info(f"Node 'search_logs': Search step {state['investigation_step']} for '{state['investigation_query']}'")
        search_result = search_logs(state["investigation_query"]) 
        
        found = "log trouvé" in search_result.lower() # Convertir en minuscules pour la comparaison
        updated_step = state["investigation_step"] + 1
        new_messages = state['messages'] + [AIMessage(content=f"Log search for '{state['investigation_query']}' : {search_result}")]
        
        # Base update dictionary
        updates = {
            "messages": new_messages,
            "investigation_step": updated_step,
            "logs_found": found, # This is the crucial update
        }
        
        # If nothing is found and we are continuing, use LLM to propose new query
        if not found and updated_step <= state["max_investigation_steps"]:
            llm_thought_prompt = ChatPromptTemplate.from_messages([
                SystemMessage("You are a log search expert. If a search yielded no results, propose a slight variation of the query for the next attempt. Be concise and give only the new query."),
                HumanMessage(f"Search for '{state['investigation_query']}' yielded no results. Propose a concise alternative query.")
            ])
            llm_response_obj = llm_client.invoke(llm_thought_prompt.format_messages())
            new_query = llm_response_obj.content.strip()
            
            updates["investigation_query"] = new_query # Update the query in the updates dict
            updates["messages"] = updates["messages"] + [AIMessage(content=f"LLM suggestion for next search: {new_query}")] # Append LLM suggestion

        return updates # Return the consolidated updates dict
    
    # Nœud 3: Fournir la réponse finale ou échouer
    def finalize_investigation_node(state: AgentState):
        logger.info("Node 'finalize_investigation': Finalizing investigation.")
        if state["logs_found"]:
            final_msg = "Investigation completed: Relevant logs found."
        else:
            final_msg = f"Investigation completed: No logs found after {state['investigation_step']} attempts."
        return {"messages": state['messages'] + [AIMessage(content=final_msg)], "final_result": final_msg} # Use state['messages']

    # Loop routing function
    def continue_investigation(state: AgentState) -> str:
        logger.info(f"Routing function 'continue_investigation' called. Current state: logs_found={state['logs_found']}, investigation_step={state['investigation_step']}")
        if state["logs_found"]:
            logger.info("Loop condition: Logs found, exiting.")
            return "end_investigation" # Logs found, exit
        if state["investigation_step"] >= state["max_investigation_steps"]:
            logger.info("Loop condition: Max attempts reached, exiting.")
            return "end_investigation" # Max attempts reached, exit
        logger.info(f"Loop condition: Continuing investigation (step {state['investigation_step']}/{state['max_investigation_steps']}).")
        return "search_logs_node"     # Continue loop

    workflow.add_node("initialize_investigation", initialize_investigation_node)
    workflow.add_node("search_logs_node", search_logs_node)
    workflow.add_node("finalize_investigation", finalize_investigation_node)

    workflow.set_entry_point("initialize_investigation")
    workflow.add_edge("initialize_investigation", "search_logs_node") # First search after init
    
    # Here, the loop: from 'search_logs_node' to 'search_logs_node' (loop) or to 'finalize_investigation' (exit)
    workflow.add_conditional_edges(
        "search_logs_node",
        continue_investigation,
        {
            "search_logs_node": "search_logs_node",      # Loop on search
            "end_investigation": "finalize_investigation" # Exit loop
        }
    )
    workflow.set_finish_point("finalize_investigation")

    return workflow.compile()
