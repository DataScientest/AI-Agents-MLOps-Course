# src/agents/human_in_loop_agent.py
import logging
from typing import List, Literal, Optional 
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import Tool
from langgraph.graph import StateGraph, START, END 

from src.state import AgentState
from tools.mlops_tools import apply_fix 

logger = logging.getLogger(__name__)

# --- Pattern 4 : Human-in-the-Loop (Fix Approval Agent) ---
def create_human_in_loop_agent(llm_client: ChatGroq, tools_for_graph: List[Tool]):
    workflow = StateGraph(AgentState)

    # Node 1: Propose a corrective action (LLM)
    def propose_action_node(state: AgentState):
        logger.info(f"Node 'propose_action': Action proposal.")
        
        # --- MODIFICATION ICI : Récupération plus robuste de problem_description ---
        # Cherche le premier HumanMessage (qui est l'input original)
        original_problem_message_content = "Problem not specified."
        for msg in state['messages']:
            if isinstance(msg, HumanMessage) and msg.content and not msg.content.startswith("Human intervention required:"):
                original_problem_message_content = msg.content
                break
        problem_description = original_problem_message_content

        llm_prompt = ChatPromptTemplate.from_messages([
            SystemMessage(
                "You are a problem analysis agent. Your task is to propose a simple and safe corrective action "
                "for the problem described. The action should be DIRECTLY APPLICABLE, like 'Restart service X' or 'Deploy config Y'. "
                "Be concise and propose ONLY ONE CONCRETE action, not a question or a general statement."
            ),
            HumanMessage(f"Problem: {problem_description}. What CONCRETE corrective action do you propose?")
        ])
        llm_response = llm_client.invoke(llm_prompt.format_messages()).content
        
        # Add a clear indicator that this is the proposed action
        return {
            "proposed_action": llm_response.strip(),
            # Append to existing messages
            "messages": state['messages'] + [ # state['messages'] est garanti d'être une liste ici
                AIMessage(content=f"Proposed action: '{llm_response.strip()}'. Awaiting human approval."),
                HumanMessage(content="Human intervention required: Please provide feedback ('approved' or 'rejected') via 'human_feedback' state update.")
            ]
        }

    # Node 2: This node is a pass-through, serving as the point where routing occurs.
    def feedback_decision_node(state: AgentState):
        logger.info(f"Node 'feedback_decision_node': Graph has reached decision point for human feedback. Current human_feedback: {state.get('human_feedback')}")
        return state

    # Node 3a: Apply the action (uses ApplyFix tool)
    def apply_action_node(state: AgentState):
        logger.info(f"Node 'apply_action': Applying approved action: '{state['proposed_action']}'")
        result = apply_fix(state["proposed_action"])
        final_msg = f"Action applied: {result}"
        
        return {"messages": state['messages'] + [AIMessage(content=final_msg)], "final_result": final_msg} # Appends to existing

    # Node 3b: Reject the action
    def reject_action_node(state: AgentState):
        logger.info(f"Node 'reject_action': Action rejected by human.")
        final_msg = f"Action rejected by human. Feedback: {state['human_feedback']}. End."
        
        return {"messages": state['messages'] + [AIMessage(content=final_msg)], "final_result": final_msg} # Appends to existing

    # Routing function (remains the same)
    def route_on_feedback(state: AgentState) -> str:
        logger.info(f"Routing function 'route_on_feedback' : human_feedback={state.get('human_feedback')}")
        if state.get("human_feedback") == "approved":
            logger.info("Human feedback: Approved. Routing to apply_action.")
            return "apply_action"
        elif state.get("human_feedback") == "rejected":
            logger.info("Human feedback: Rejected. Routing to reject_action.")
            return "reject_action"
        else:
            logger.info("No human feedback received yet. Routing to 'await_and_end' to pause current invoke and await external update.")
            return "await_and_end"

    workflow.add_node("propose_action", propose_action_node)
    workflow.add_node("feedback_decision_node", feedback_decision_node)
    workflow.add_node("apply_action", apply_action_node)
    workflow.add_node("reject_action", reject_action_node)

    workflow.set_entry_point("propose_action")
    workflow.add_edge("propose_action", "feedback_decision_node")

    workflow.add_conditional_edges(
        "feedback_decision_node",
        route_on_feedback,
        {
            "apply_action": "apply_action",
            "reject_action": "reject_action",
            "await_and_end": END 
        }
    )

    workflow.set_finish_point("apply_action")
    workflow.set_finish_point("reject_action")

    return workflow.compile()
