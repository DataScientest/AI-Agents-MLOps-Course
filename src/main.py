# src/main.py
import os
import logging
from typing import List

from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.tools import Tool
from langchain_core.messages import HumanMessage, AIMessage # AIMessage for final results from graph

# Import local files
from tools.mlops_tools import (
    get_system_metrics, GetSystemMetricsInput,
    check_alert_severity, CheckAlertSeverityInput,
    search_logs, SearchLogsInput,
    apply_fix, ApplyFixInput,
    Calculator, CalculatorInput
)
from src.state import AgentState # Our graph state

# Import pattern agents
from src.agents.linear_agent import create_linear_report_agent
from src.agents.conditional_agent import create_alert_router_agent
from src.agents.loop_agent import create_log_investigator_agent
from src.agents.human_in_loop_agent import create_human_in_loop_agent

# logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Load environment variables ---
load_dotenv()

# --- 1. LLM Initialization (common to all graphs) ---
groq_api_key = os.getenv("GROQ_API_KEY")
if not groq_api_key:
    logger.error("The GROQ_API_KEY environment variable is not set. Please configure it in the .env file.")
    exit(1) # Stop execution if key is missing

try:
    llm = ChatGroq(
        temperature=0,
        model_name="llama-3.1-8b-instant",
        groq_api_key=groq_api_key
    )
    logger.info(f"Groq LLM client '{llm.model_name}' initialized successfully.")
except Exception as e:
    logger.error(f"Error initializing Groq LLM: {e}")
    exit(1)

# --- 2. Definition of ALL available tools (common) ---
# Note that each graph will only use a subset of these tools.
all_tools = [
    Tool(
        name="Calculatrice",
        func=Calculator,
        description="Useful for performing arithmetic operations and mathematical functions (e.g., sqrt, log, sin). Takes a FORMAL mathematical expression as a string, e.g., '2 + 2 * 3' or 'sqrt(144) + 5'. The Action Input must be THE EXPRESSION WITHOUT ANY ADDITIONAL QUOTES around the expression itself.",
        args_schema=CalculatorInput
    ),
    Tool(
        name="GetSystemMetrics",
        func=get_system_metrics,
        description="Retrieves usage metrics for system components such as 'CPU', 'Memory', 'Disk'.",
        args_schema=GetSystemMetricsInput
    ),
    Tool(
        name="CheckAlertSeverity",
        func=check_alert_severity,
        description="Checks the severity of an alert description. Returns 'critical', 'medium', or 'low'.",
        args_schema=CheckAlertSeverityInput
    ),
    Tool(
        name="SearchLogs",
        func=search_logs,
        description="Searches for a specific term in system logs. Can return an excerpt or 'No relevant logs found'.",
        args_schema=SearchLogsInput
    ),
    Tool(
        name="ApplyFix",
        func=apply_fix,
        description="Applies a corrective fix or action. Takes a description of the fix to be applied.",
        args_schema=ApplyFixInput
    ),
]
logger.info(f"{len(all_tools)} tools available in total.")


# ----------------------------------------------------------------------------------------------------------------------
# Main function to execute LangGraph agents
# ----------------------------------------------------------------------------------------------------------------------
def main():
    # --- Create LangGraph agent instances for each pattern ---
    logger.info("Creating LangGraph agents for each pattern...")
    # For each agent, we only pass the relevant tools
    # Note: create_llm_tool_agent_node will be used internally by some of these agents
    # so they need access to appropriate tools when constructing their internal LLM agent.
    
    # We pass all_tools to allow the internal LLM nodes to decide.
    # In a real scenario, you'd pass a subset to restrict LLM's tool choice.
    # For this exercise, we pass all_tools to simplify.
    linear_agent = create_linear_report_agent(llm, all_tools) 
    alert_router_agent = create_alert_router_agent(llm, all_tools)
    log_investigator_agent = create_log_investigator_agent(llm, all_tools)
    human_in_loop_agent = create_human_in_loop_agent(llm, all_tools)
    logger.info("LangGraph agents created.")

    # --- Test Pattern 1: Linear Workflow ---
    print("\n--- TEST : Linear Workflow (Basic Health Report Agent) ---")
    initial_state_linear = AgentState(messages=[HumanMessage(content="Generate a CPU health report.")], system_metrics={})
    # LangGraph invoke returns the final state. The final message is in messages[-1].
    final_state_linear = linear_agent.invoke(initial_state_linear)
    print(f"Final Answer (Linear): {final_state_linear['messages'][-1].content}")
    print("----------------------------------------------------------------")

    # --- Test Pattern 2: Conditional Branching ---
    print("\n--- TEST : Conditional Branching (Alert Routing Agent) ---")
    # Test 1: Critical Alert
    initial_state_critical = AgentState(messages=[HumanMessage(content="Alert: Critical service outage on production server!")], alert_info="Critical service outage on production server!")
    final_state_critical = alert_router_agent.invoke(initial_state_critical)
    print(f"Final Answer (Critical Alert): {final_state_critical['messages'][-1].content}")
    
    # Test 2: Medium Alert
    initial_state_medium = AgentState(messages=[HumanMessage(content="Alert: High CPU usage on ML analysis service.")], alert_info="High CPU usage on ML analysis service.")
    final_state_medium = alert_router_agent.invoke(initial_state_medium)
    print(f"Final Answer (Medium Alert): {final_state_medium['messages'][-1].content}")
    print("----------------------------------------------------------------")

    # --- Test Pattern 3: Loop with Conditions ---
    print("\n--- TEST : Loop with Conditions (Log Investigation Agent) ---")
    # Test 1: Term found (should loop a few times if random doesn't find it on first attempt)
    initial_state_loop_found = AgentState(messages=[HumanMessage(content="Find logs concerning 'error'.")], investigation_query="error", max_investigation_steps=5)
    final_state_loop_found = log_investigator_agent.invoke(initial_state_loop_found)
    print(f"Final Answer (Logs Found): {final_state_loop_found['messages'][-1].content}")

    # Test 2: Term not found after max attempts
    initial_state_loop_not_found = AgentState(messages=[HumanMessage(content="Find logs for 'non_existent_log_pattern'.")], investigation_query="non_existent_log_pattern", max_investigation_steps=2)
    final_state_loop_not_found = log_investigator_agent.invoke(initial_state_loop_not_found)
    print(f"Final Answer (Logs Not Found): {final_state_loop_not_found['messages'][-1].content}")
    print("----------------------------------------------------------------")

    # --- Test Pattern 4: Human-in-the-Loop ---
    print("\n--- TEST : Human-in-the-Loop (Fix Approval Agent) ---")
    
    original_problem_description = "Problem: ML scoring service returns high latencies."
    
    # The initial state for the first run (proposal phase)
    # Ensure all required fields are initialized, even if empty.
    initial_proposal_state_hil = AgentState(
        messages=[HumanMessage(content=original_problem_description)],
        proposed_action="", human_feedback="",
        alert_info="", alert_severity="unknown",
        investigation_query="", investigation_step=0, max_investigation_steps=0, logs_found=False,
        system_metrics={}, report_content="",
        final_result=None
    )
    
    print("Agent proposes an action and implicitly awaits human approval (by ending the current invoke)...")
    
    # Use invoke() for the first part, as it's designed to run until END and return the full state.
    # This invoke will run 'propose_action_node', 'feedback_decision_node', then 'route_on_feedback' will return END.
    # invoke() will then return the full, aggregated state *before* END.
    current_state_hil = human_in_loop_agent.invoke(initial_proposal_state_hil)
    
    proposed_action = current_state_hil.get("proposed_action", "No action proposed.")
    print(f"Agent proposed: '{proposed_action}'")
    print("Graph has ended (implicitly paused) awaiting human approval.")


    # Simulate human approval
    print("Simulating human approval (Approved)...")
    
    # Create the state to resume from.
    # We take the state from BEFORE it ended, and inject the human feedback.
    # This state will be the NEW entry point for the graph.
    resumed_state_approved = current_state_hil.copy()
    resumed_state_approved["human_feedback"] = "approved"
    
    # Use invoke() again to resume. It will take the updated state, route to apply_action, and run to END.
    final_state_approved = human_in_loop_agent.invoke(resumed_state_approved)
    
    # Access messages safely - this check remains important
    if final_state_approved and 'messages' in final_state_approved and final_state_approved['messages']:
        print(f"Final Answer (Human Approved): {final_state_approved['messages'][-1].content}")
    else:
        print(f"Final Answer (Human Approved): No final message in state or state is empty. Full state: {final_state_approved}")


    # Simulate human rejection
    print("\nSimulating human rejection (Rejected)...")
    
    # Re-run the initial proposal phase to get the proposed_action again
    # This ensures a clean state for the rejection test, as invoke() with a new state starts a new run.
    rejection_initial_state = initial_proposal_state_hil.copy() # Fresh state for rejection path
    current_state_for_rejection = human_in_loop_agent.invoke(rejection_initial_state) # Run until END again
    
    proposed_action_for_rejection = current_state_for_rejection.get("proposed_action", "No action proposed.")

    # Create the state to resume for rejection.
    resumed_state_rejected = current_state_for_rejection.copy()
    resumed_state_rejected["human_feedback"] = "rejected"
    
    final_state_rejected = human_in_loop_agent.invoke(resumed_state_rejected) # Resume with updated state

    if final_state_rejected and 'messages' in final_state_rejected and final_state_rejected['messages']:
        print(f"Final Answer (Human Rejected): {final_state_rejected['messages'][-1].content}")
    else:
        print(f"Final Answer (Human Rejected): No final message in state or state is empty. Full state: {final_state_rejected}")

    print("----------------------------------------------------------------")


if __name__ == "__main__":
    main()
