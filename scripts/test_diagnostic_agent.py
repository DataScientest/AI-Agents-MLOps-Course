#!/usr/bin/env python3
"""Test script to run the diagnostic agent with LangSmith tracing enabled."""

import os
import sys
from pathlib import Path

# Add src directory to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src" / "aiops_agent_monitor"))

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq

from agents.diagnostic import build_diagnostic_agent
from state import AgentState
from tools.mlops_tools import PrometheusQuery, LokiLogSearch, GrafanaDashboardLink

# Load environment variables (including LangSmith config)
load_dotenv(override=True)

# Override URLs for localhost access (not inside Docker)
os.environ["PROMETHEUS_URL"] = "http://localhost:9091"
os.environ["LOKI_URL"] = "http://localhost:3100"
os.environ["GRAFANA_URL"] = "http://localhost:3001"

def main():
    """Run a diagnostic agent test with LangSmith tracing."""

    # Verify LangSmith is configured
    langchain_api_key = os.getenv("LANGCHAIN_API_KEY")
    langchain_tracing = os.getenv("LANGCHAIN_TRACING_V2")
    langchain_project = os.getenv("LANGCHAIN_PROJECT", "default")

    print(f"LangSmith Configuration:")
    print(f"  LANGCHAIN_TRACING_V2: {langchain_tracing}")
    print(f"  LANGCHAIN_API_KEY: {'*' * 20 if langchain_api_key else 'NOT SET'}")
    print(f"  LANGCHAIN_PROJECT: {langchain_project}")

    if not langchain_api_key or langchain_tracing != "true":
        print("\nWARNING: LangSmith tracing not properly configured!")
        print("Set LANGCHAIN_TRACING_V2=true and LANGCHAIN_API_KEY in .env")
    else:
        print(f"\nLangSmith tracing ENABLED")

    # Initialize LLM
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        print("ERROR: GROQ_API_KEY environment variable not set.")
        sys.exit(1)

    model_name = os.getenv("GROQ_MODEL_NAME", "llama-3.3-70b-versatile")
    llm = ChatGroq(temperature=0, model_name=model_name, groq_api_key=groq_api_key)
    print(f"Initialized LLM: {model_name}")

    # Initialize tools
    tools = [PrometheusQuery, LokiLogSearch, GrafanaDashboardLink]
    print(f"Loaded {len(tools)} diagnostic tools")

    # Build the agent graph
    agent = build_diagnostic_agent(llm, tools)
    print("Built diagnostic agent graph")

    # Create test alert
    alert_info = "High CPU usage detected on news-classifier-api service (85% for 5 minutes)"
    print(f"\n{'='*60}")
    print(f"Test Alert: {alert_info}")
    print(f"{'='*60}\n")

    # Build initial state
    initial_state = AgentState(
        messages=[HumanMessage(content=f"Diagnose this alert: {alert_info}")],
        alert_info=alert_info,
        alert_severity="unknown",
        prometheus_data="",
        loki_logs="",
        grafana_link="",
        final_result=None,
    )

    # Run the agent (this will generate a LangSmith trace)
    print("Running diagnostic agent...")
    print("(Check LangSmith UI for trace visualization)\n")

    try:
        final_state = agent.invoke(initial_state)

        # Extract final diagnosis
        messages = final_state.get("messages", [])
        final_message = messages[-1].content if messages else "No diagnosis generated"

        print(f"\n{'='*60}")
        print("Agent Diagnosis:")
        print(f"{'='*60}")
        print(final_message)
        print(f"{'='*60}\n")

        # Show trace information
        if os.getenv("LANGCHAIN_API_KEY"):
            print(f"View trace at: https://smith.langchain.com/")
            print(f"Project: {os.getenv('LANGCHAIN_PROJECT', 'default')}\n")

        return 0

    except Exception as e:
        print(f"\nERROR: Agent execution failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
