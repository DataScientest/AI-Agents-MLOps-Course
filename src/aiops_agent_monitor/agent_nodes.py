import logging
from typing import List, Any, Optional

from langchain_groq import ChatGroq
from langchain_core.tools import Tool
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage, ToolMessage 
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain.agents import create_react_agent
from langgraph.prebuilt import ToolNode

from state import AgentState

logger = logging.getLogger(__name__)

def create_llm_tool_agent_node(llm: ChatGroq, tools_for_node: List[Tool]):
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

    agent_runnable = create_react_agent(llm, tools_for_node, react_prompt)
    
    def agent_node(state: AgentState):
        logger.info(f"Entering agent_node (LLM Tool Agent).")
        
        user_input_message = ""
        for msg in reversed(state['messages']):
            if isinstance(msg, HumanMessage):
                user_input_message = msg.content
                break
        
        if not user_input_message:
            logger.error("No HumanMessage found for agent input.")
            return {"messages": [AIMessage(content="Error: No user input for the agent.")]}
        
        scratchpad_for_llm: List[BaseMessage] = []
        MAX_SCRATCHPAD_LENGTH = 10
        
        for msg in reversed(state.get("messages", [])):
            if isinstance(msg, AIMessage) and msg.tool_calls:
                scratchpad_for_llm.insert(0, msg)
            elif isinstance(msg, HumanMessage) and msg.name == "tool_output":
                scratchpad_for_llm.insert(0, msg)
            elif isinstance(msg, AIMessage) and not msg.tool_calls:
                scratchpad_for_llm.insert(0, msg)
            
            if len(scratchpad_for_llm) >= MAX_SCRATCHPAD_LENGTH:
                break
        
        logger.debug(f"Passing scratchpad of length {len(scratchpad_for_llm)} to agent_runnable.")

        result = agent_runnable.invoke({
            "input": user_input_message,
            "tools": tools_for_node,
            "tool_names": [t.name for t in tools_for_node],
            "agent_scratchpad": scratchpad_for_llm
        })
        
        if isinstance(result, dict) and "output" in result:
             return {"messages": state['messages'] + [AIMessage(content=result["output"])]}
        
        if isinstance(result, AIMessage) and result.tool_calls:
            return {"messages": state['messages'] + [result]}
        elif isinstance(result, AIMessage) and result.content:
            return {"messages": state['messages'] + [result]}

        logger.warning(f"agent_node produced an unexpected result: {result}. Typically, LangGraph expects an AIMessage or a dict with 'output'.")
        return {"messages": state['messages'] + [AIMessage(content=f"Agent could not provide a final answer or clear action: {result}")]}

    return agent_node

def get_tool_node(all_available_tools: List[Tool]):
    return ToolNode(all_available_tools)
