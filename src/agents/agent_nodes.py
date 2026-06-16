# src/agent_nodes.py
import logging
from typing import List

from langchain_groq import ChatGroq
from langchain_core.tools import Tool
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langgraph.prebuilt import ToolNode, create_react_agent

from src.state import AgentState # Import our graph state

logger = logging.getLogger(__name__)

# --- Definition of a generic agent node for LLMs with tools ---
# This node can be reused in different graphs for agent logic.
# It encapsulates the logic of a LangGraph ReAct agent within a graph node.
def create_llm_tool_agent_node(llm: ChatGroq, tools_for_node: List[Tool]):
    # LangGraph's prebuilt ReAct agent handles the tool loop directly.
    system_prompt = (
        "You are an AI assistant capable of using tools to solve problems. "
        "Use the available tools when they help answer the user's request, "
        "then provide a concise final answer."
    )

    agent_runnable = create_react_agent(llm, tools_for_node, prompt=system_prompt)
    
    # The node that interacts with the state and calls the Runnable agent.
    # In LangGraph, a node takes the state and returns state updates.
    def agent_node(state: AgentState):
        logger.info(f"Entering agent_node (LLM Tool Agent).")
        
        # The HumanMessage should be the last user input.
        user_input_message = ""
        for msg in reversed(state['messages']):
            if isinstance(msg, HumanMessage):
                user_input_message = msg.content
                break
        
        if not user_input_message:
            logger.error("No HumanMessage found for agent input.")
            # Return an error message if input is missing
            return {"messages": [AIMessage(content="Error: No user input for the agent.")]}

        result = agent_runnable.invoke({"messages": state.get("messages", [HumanMessage(content=user_input_message)])})

        if isinstance(result, dict) and result.get("messages"):
            final_message = result["messages"][-1]
            if isinstance(final_message, BaseMessage):
                return {"messages": [final_message]}
        
        # If the agent produced an AgentAction (decision to use a tool),
        # LangGraph expects this to be the last message that will be consumed by the ToolNode.
        # The ToolNode must be branched directly after this node.
        if isinstance(result, AIMessage) and result.tool_calls:
            # If the LLM directly generates an AIMessage with tool_calls, that's what we return.
            return {"messages": [result]}
        elif isinstance(result, AIMessage) and result.content:
            return {"messages": [result]}

        logger.warning(f"agent_node produced an unexpected result: {result}. Typically, LangGraph expects an AIMessage or a dict with 'output'.")
        return {"messages": [AIMessage(content=f"Agent could not provide a final answer or clear action: {result}")]}

    return agent_node


# --- Definition of a generic tool call node ---
# Uses LangGraph ToolNode, which is already optimized for this.
# It takes the last message (which should be an AgentAction or a Tool_call) and executes it.
def get_tool_node(all_available_tools: List[Tool]):
    return ToolNode(all_available_tools)
