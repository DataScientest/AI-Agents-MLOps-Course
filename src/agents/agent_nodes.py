# src/agent_nodes.py
import logging
from typing import List

from langchain_groq import ChatGroq
from langchain_core.tools import Tool
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain.agents import create_react_agent
from langgraph.prebuilt import ToolNode

from src.state import AgentState # Import our graph state

logger = logging.getLogger(__name__)

# --- Definition of a generic agent node for LLMs with tools ---
# This node can be reused in different graphs for agent logic.
# It encapsulates the logic of a LangChain AgentExecutor within a LangGraph node.
def create_llm_tool_agent_node(llm: ChatGroq, tools_for_node: List[Tool]):
    # We construct the ReAct prompt here, which is crucial for parsing.
    react_system_template = (
        "You are an AI assistant capable of using tools to solve problems. "
        "You have access to the following tools:\n"
        "{tools}\n\n"
        "Use the following format to respond:\n\n"
        "Question: the question you need to solve\n"
        "Thought: you should always think about what to do\n"
        "Action: the action to take, must be one of [{tool_names}]\n"
        "Action Input: the input to the action\n"
        "Observation: the result of the action\n"
        "...\n"
        "Thought: I now know the final answer\n"
        "Final Answer: the final answer to the original question\n\n"
        "Always start with your \"Thought\"."
    )
    system_message_prompt = SystemMessagePromptTemplate.from_template(react_system_template)
    human_message_prompt = HumanMessagePromptTemplate.from_template("{input}\n{agent_scratchpad}")

    react_prompt = ChatPromptTemplate(
        messages=[system_message_prompt, human_message_prompt],
        input_variables=['agent_scratchpad', 'input', 'tools', 'tool_names']
    )

    # Create the Runnable agent (a simple LangChain agent that follows the ReAct prompt)
    agent_runnable = create_react_agent(llm, tools_for_node, react_prompt)
    
    # The node that interacts with the state and calls the Runnable agent.
    # In LangGraph, a node takes the state and returns state updates.
    def agent_node(state: AgentState):
        logger.info(f"Entering agent_node (LLM Tool Agent).")
        
        # The HumanMessage should be the last user input.
        # The AgentExecutor expects a string 'input'.
        user_input_message = ""
        for msg in reversed(state['messages']):
            if isinstance(msg, HumanMessage):
                user_input_message = msg.content
                break
        
        if not user_input_message:
            logger.error("No HumanMessage found for agent input.")
            # Return an error message if input is missing
            return {"messages": [AIMessage(content="Error: No user input for the agent.")]}

                # Construct agent_scratchpad from existing messages, filtering for agent's own steps
        # and limiting the length to prevent LangSmith overflow.
        
        # The 'agent_scratchpad' for create_react_agent should contain the Thought/Action/Observation history.
        # These are typically AIMessage (for Thought/Action) and HumanMessage with tool_output name (for Observation).
        scratchpad_for_llm: List[BaseMessage] = []
        MAX_SCRATCHPAD_LENGTH = 10 # Limit to last 10 agent-related messages in scratchpad
        
        # Iterate over messages in reverse to get the most recent ones first
        # and filter for agent's internal monologue
        for msg in reversed(state.get("messages", [])):
            if isinstance(msg, AIMessage) and msg.tool_calls: # AI's action message
                scratchpad_for_llm.insert(0, msg) # Insert at beginning to maintain chronological order
            elif isinstance(msg, HumanMessage) and msg.name == "tool_output": # Tool output observation
                scratchpad_for_llm.insert(0, msg)
            elif isinstance(msg, AIMessage) and not msg.tool_calls: # AI's thought/response message
                scratchpad_for_llm.insert(0, msg)
            
            if len(scratchpad_for_llm) >= MAX_SCRATCHPAD_LENGTH:
                break
        
        logger.debug(f"Passing scratchpad of length {len(scratchpad_for_llm)} to agent_runnable.")

        # Invoke the Runnable agent with state information
        # We pass an empty list for agent_scratchpad if messages is not yet defined
        result = agent_runnable.invoke({
            "input": user_input_message,
            "tools": tools_for_node,
            "tool_names": [t.name for t in tools_for_node],
            "agent_scratchpad": state.get("messages", []) # Conversation history serves as scratchpad
        })
        
        # The result can be either a 'Final Answer' (dictionary with 'output'),
        # or an `AgentAction` (if the agent decides to use a tool).
        
        # If the agent produced a Final Answer
        if isinstance(result, dict) and "output" in result:
             return {"messages": [AIMessage(content=result["output"])]}
        
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
