# src/main.py
"""
Main script to demonstrate LangGraph agent patterns.

Usage (from project root):
    python -m src.main                      # Run all patterns
    python -m src.main --pattern linear     # Run linear workflow only
    python -m src.main --pattern conditional # Run conditional branching only
    python -m src.main --pattern loop       # Run loop pattern only
    python -m src.main --pattern human      # Run human-in-the-loop only
"""
import os
import sys
import argparse
import logging
from typing import Optional

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage

# Import pattern agents
from src.agents.linear_agent import create_linear_report_agent
from src.agents.conditional_agent import create_alert_router_agent
from src.agents.loop_agent import create_log_investigator_agent
from src.agents.human_in_loop_agent import create_human_in_loop_agent
from src.state import AgentState

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_llm() -> ChatGroq:
    """Initialize and return the LLM client."""
    load_dotenv(override=True)

    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        logger.error("GROQ_API_KEY not found. Please set it in .env file.")
        sys.exit(1)

    try:
        llm = ChatGroq(
            temperature=0,
            model_name="llama-3.1-8b-instant",
            groq_api_key=groq_api_key
        )
        logger.info(f"✓ LLM initialized: {llm.model_name}")
        return llm
    except Exception as e:
        logger.error(f"Failed to initialize LLM: {e}")
        sys.exit(1)


def run_linear_pattern(llm: ChatGroq) -> None:
    """Run Pattern 0: Linear Workflow - Health Report Agent."""
    print("\n" + "="*70)
    print("PATTERN 0: Linear Workflow (Health Report Agent)")
    print("="*70)

    agent = create_linear_report_agent(llm, [])

    initial_state = AgentState(
        messages=[HumanMessage(content="Generate a CPU health report.")],
        system_metrics={}
    )

    final_state = agent.invoke(initial_state)

    print(f"\n✓ Result: {final_state['messages'][-1].content}")
    print("-"*70)


def run_conditional_pattern(llm: ChatGroq) -> None:
    """Run Pattern 1: Conditional Branching - Alert Router Agent."""
    print("\n" + "="*70)
    print("PATTERN 1: Conditional Branching (Alert Router Agent)")
    print("="*70)

    agent = create_alert_router_agent(llm, [])

    # Test critical alert
    print("\n[Test 1: Critical Alert]")
    state_critical = AgentState(
        messages=[HumanMessage(content="Alert: Critical service outage on production server!")],
        alert_info="Critical service outage on production server!"
    )
    result_critical = agent.invoke(state_critical)
    print(f"✓ Result: {result_critical['messages'][-1].content}")

    # Test medium alert
    print("\n[Test 2: Medium Alert]")
    state_medium = AgentState(
        messages=[HumanMessage(content="Alert: High CPU usage on ML analysis service.")],
        alert_info="High CPU usage on ML analysis service."
    )
    result_medium = agent.invoke(state_medium)
    print(f"✓ Result: {result_medium['messages'][-1].content}")
    print("-"*70)


def run_loop_pattern(llm: ChatGroq) -> None:
    """Run Pattern 2: Loop with Conditions - Log Investigator Agent."""
    print("\n" + "="*70)
    print("PATTERN 2: Loop with Conditions (Log Investigator Agent)")
    print("="*70)

    agent = create_log_investigator_agent(llm, [])

    # Test with term that might be found
    print("\n[Test 1: Search for 'error' logs]")
    state_found = AgentState(
        messages=[HumanMessage(content="Find logs concerning 'error'.")],
        investigation_query="error",
        max_investigation_steps=5
    )
    result_found = agent.invoke(state_found)
    print(f"✓ Result: {result_found['messages'][-1].content}")

    # Test with term that won't be found
    print("\n[Test 2: Search for non-existent pattern]")
    state_not_found = AgentState(
        messages=[HumanMessage(content="Find logs for 'non_existent_log_pattern'.")],
        investigation_query="non_existent_log_pattern",
        max_investigation_steps=2
    )
    result_not_found = agent.invoke(state_not_found)
    print(f"✓ Result: {result_not_found['messages'][-1].content}")
    print("-"*70)


def run_human_loop_pattern(llm: ChatGroq) -> None:
    """Run Pattern 3: Human-in-the-Loop - Fix Approval Agent."""
    print("\n" + "="*70)
    print("PATTERN 3: Human-in-the-Loop (Fix Approval Agent)")
    print("="*70)

    agent = create_human_in_loop_agent(llm, [])

    problem = "Problem: ML scoring service returns high latencies."

    initial_state = AgentState(
        messages=[HumanMessage(content=problem)],
        proposed_action="",
        human_feedback="",
        alert_info="",
        alert_severity="unknown",
        investigation_query="",
        investigation_step=0,
        max_investigation_steps=0,
        logs_found=False,
        system_metrics={},
        report_content="",
        final_result=None
    )

    # First invoke: Agent proposes action
    print("\n[Step 1: Agent proposes action]")
    current_state = agent.invoke(initial_state)
    proposed_action = current_state.get("proposed_action", "No action proposed.")
    print(f"Proposed action: {proposed_action}")
    print("⏸️  Graph paused, awaiting human approval...")

    # Simulate human approval
    print("\n[Step 2: Human approves action]")
    approved_state = current_state.copy()
    approved_state["human_feedback"] = "approved"
    final_approved = agent.invoke(approved_state)

    if final_approved.get('messages'):
        print(f"✓ Result (Approved): {final_approved['messages'][-1].content}")

    # Simulate human rejection
    print("\n[Step 3: Testing rejection path]")
    rejection_state = agent.invoke(initial_state)  # Fresh proposal
    rejected_state = rejection_state.copy()
    rejected_state["human_feedback"] = "rejected"
    final_rejected = agent.invoke(rejected_state)

    if final_rejected.get('messages'):
        print(f"✓ Result (Rejected): {final_rejected['messages'][-1].content}")

    print("-"*70)


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Run LangGraph agent pattern demonstrations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.main                      # Run all patterns
  python -m src.main --pattern linear     # Run linear workflow only
  python -m src.main --pattern loop       # Run loop pattern only
        """
    )

    parser.add_argument(
        '--pattern',
        '-p',
        choices=['linear', 'conditional', 'loop', 'human', 'all'],
        default='all',
        help='Which pattern to run (default: all)'
    )

    args = parser.parse_args()

    # Setup
    print("\n" + "="*70)
    print("LangGraph Agent Patterns - Chapter 2 Demo")
    print("="*70)

    llm = setup_llm()

    # Pattern execution mapping
    patterns = {
        'linear': run_linear_pattern,
        'conditional': run_conditional_pattern,
        'loop': run_loop_pattern,
        'human': run_human_loop_pattern,
    }

    # Run requested pattern(s)
    if args.pattern == 'all':
        for pattern_name, pattern_func in patterns.items():
            pattern_func(llm)
    else:
        patterns[args.pattern](llm)

    print("\n" + "="*70)
    print("✓ Demo completed successfully!")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
