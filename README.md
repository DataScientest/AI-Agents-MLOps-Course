# AI Agents MLOps Course - Chapter 2: LangGraph - Agent Orchestration

This branch contains the completed practical exercise for Chapter 2, focusing on mastering LangGraph to create structured agent workflows using essential patterns.

## Exercise Principle

Chapter 2 delves into LangGraph, a powerful library for building multi-actor agent applications as state graphs. Students learn fundamental concepts like `State`, `Nodes`, `Edges`, and `StateGraph`.

This exercise implements four distinct LangGraph agents, each demonstrating a key architectural pattern, within the context of our "MLOps Guard Agent" mission:
1.  **Linear Workflow:** A basic health report agent that sequentially fetches CPU metrics and generates a report.
2.  **Conditional Branching:** An alert router agent that evaluates alert severity (critical, medium, low) and dispatches it to different handling branches.
3.  **Loop with Conditions:** A log investigator agent that iteratively searches for log patterns until found or a maximum number of attempts is reached, using the LLM to refine search queries.
4.  **Human-in-the-Loop:** A fix approval agent that proposes a corrective action and pauses for human approval/rejection before proceeding.

The primary goal is to provide hands-on experience with:
- Defining graph `State` with `TypedDict` and custom message aggregation.
- Implementing various node types (pure Python functions, LLM-driven decision nodes using `create_llm_tool_agent_node`, and `ToolNode` for tool execution).
- Configuring graph `Entry Points`, `Edges`, and `Conditional Edges` for complex control flows.
- Understanding how to integrate custom logic and external tools within a LangGraph workflow.
- Leveraging LangSmith for visual debugging of complex graph executions.

## Project Structure

```
AI-Agents-MLOps-Course/
├── .env # Environment variables (GROQ_API_KEY, LangSmith config)
├── src/
│ ├── init.py
│ ├── main.py # Main script: LLM setup, all tool definitions, and testing of each LangGraph agent
│ ├── state.py # Defines the shared AgentState (TypedDict) for all graphs
│ ├── agent_nodes.py # Utility functions for common LangGraph nodes (LLM tool agent, ToolNode)
│ └── agents/ # Directory containing the code for each pattern agent
│ ├── init.py
│ ├── linear_agent.py # Implements the Linear Workflow pattern
│ ├── conditional_agent.py # Implements the Conditional Branching pattern
│ ├── loop_agent.py # Implements the Loop with Conditions pattern
│ └── human_in_loop_agent.py # Implements the Human-in-the-Loop pattern
├── requirements.txt # Python dependencies
├── prompts/
│ └── system_prompt.txt # Basic persona for LLM nodes
└── tools/
├── init.py
├── calculator.py # Calculator tool (from Chapter 1)
└── mlops_tools.py # Simulated MLOps tools (metrics, alerts, logs, fixes)
```

## How to Run the Project

This project uses `uv` for dependency management and `Makefile` for simplified commands.

### 1. Prerequisites

*   **Python 3.9+** installed.
*   **`uv` installed:** `pip install uv` (or use `pip` directly for dependency management).
*   **Git** installed.
*   **Groq API Key:** Obtain a key from [Groq Cloud](https://console.groq.com/keys) and add it to your `.env` file.
*   **LangSmith API Key (Recommended for observability):** Obtain a key from [LangSmith](https://smith.langchain.com/) and add it to your `.env` file.

### 2. Setup (`.env` file)

Create a `.env` file at the root of the project:
```
GROQ_API_KEY="your_groq_api_key_here"
LANGCHAIN_TRACING_V2="true"
LANGCHAIN_API_KEY="your_langsmith_api_key_here"
LANGCHAIN_PROJECT="MLOps Guard Agent - Chapter 2 (LangGraph Patterns)"
```

### 3. Build and Run

Use the provided `Makefile` for ease of use.

*   **Install dependencies & run all LangGraph agents:**
    ```bash
    make
    ```
    This command will:
    1.  Create a virtual environment (`uv venv`).
    2.  Install dependencies from `requirements.txt` (`uv pip install -r requirements.txt`).
    3.  Activate the virtual environment.
    4.  Execute the main agent script (`python3 -m src.main`), which will run tests for all four LangGraph patterns.

### 4. Observe with LangSmith (Recommended)

While the agents run, open your browser and navigate to [https://smith.langchain.com/](https://smith.langchain.com/). Log in and find the project "MLOps Guard Agent - Chapter 2 (LangGraph Patterns)" to observe the detailed traces of each agent's execution. Pay special attention to the visual graph view for each pattern, showing the nodes, edges, and state transitions.

### 5. Expected Agents Output

```
2025-09-03 15:02:26,479 - INFO - Groq LLM client 'llama-3.1-8b-instant' initialized successfully.
2025-09-03 15:02:26,479 - INFO - 5 tools available in total.
2025-09-03 15:02:26,479 - INFO - Creating LangGraph agents for each pattern...
2025-09-03 15:02:26,574 - INFO - LangGraph agents created.

--- TEST : Linear Workflow (Basic Health Report Agent) ---
2025-09-03 15:02:27,811 - INFO - Node 'get_cpu_metrics' : Fetching CPU metrics.
2025-09-03 15:02:27,811 - INFO - Outil 'GetSystemMetrics' appelé pour le composant: 'CPU'
2025-09-03 15:02:27,811 - INFO - Métriques simulées pour 'CPU': {'usage': '48%', 'load_avg': '4.19'}
2025-09-03 15:02:27,813 - INFO - Node 'generate_report' : Generating health report.
2025-09-03 15:02:28,104 - INFO - HTTP Request: POST https://api.groq.com/openai/v1/chat/completions "HTTP/1.1 200 OK"
2025-09-03 15:02:28,120 - INFO - Node 'finalize_report': Report finalized.
Final Answer (Linear): CPU health report completed. Content: **System Health Report**

**CPU Metrics:**

- **Usage:** 48% (Above normal threshold, indicating moderate system load)
- **Load Average:** 4.19 (Above normal threshold, indicating high system load)

**Recommendation:** Monitor system performance to prevent potential bottlenecks and consider optimizing resource allocation to maintain optimal system efficiency.
----------------------------------------------------------------

--- TEST : Conditional Branching (Alert Routing Agent) ---
2025-09-03 15:02:28,122 - INFO - Node 'evaluate_alert': Evaluating alert: Critical service outage on production server!
2025-09-03 15:02:28,123 - INFO - Outil 'CheckAlertSeverity' appelé pour l'alerte: 'Critical service outage on production server!'
2025-09-03 15:02:28,123 - INFO - Detected alert severity: critical
2025-09-03 15:02:28,125 - INFO - Node 'handle_critical_alert': Critical alert (Critical service outage on production server!). Immediate escalation.
Final Answer (Critical Alert): CRITICAL alert detected. Immediate escalation to on-call pager.
2025-09-03 15:02:28,127 - INFO - Node 'evaluate_alert': Evaluating alert: High CPU usage on ML analysis service.
2025-09-03 15:02:28,127 - INFO - Outil 'CheckAlertSeverity' appelé pour l'alerte: 'High CPU usage on ML analysis service.'
2025-09-03 15:02:28,127 - INFO - Detected alert severity: low
2025-09-03 15:02:28,128 - INFO - Node 'handle_low_alert': Low alert (High CPU usage on ML analysis service.). Simple archiving.
Final Answer (Medium Alert): LOW alert detected. Archiving for later analysis.
----------------------------------------------------------------

--- TEST : Loop with Conditions (Log Investigation Agent) ---
2025-09-03 15:02:28,130 - INFO - Node 'initialize_investigation': Starting investigation for 'error'
2025-09-03 15:02:28,131 - INFO - Node 'search_logs': Search step 0 for 'error'
2025-09-03 15:02:28,131 - INFO - Outil 'SearchLogs' appelé pour le terme: 'error'
2025-09-03 15:02:28,270 - INFO - HTTP Request: POST https://api.groq.com/openai/v1/chat/completions "HTTP/1.1 200 OK"
2025-09-03 15:02:28,272 - INFO - Routing function 'continue_investigation' called. Current state: logs_found=False, investigation_step=1
2025-09-03 15:02:28,273 - INFO - Loop condition: Continuing investigation (step 1/5).
2025-09-03 15:02:28,274 - INFO - Node 'search_logs': Search step 1 for '"error message"'
2025-09-03 15:02:28,274 - INFO - Outil 'SearchLogs' appelé pour le terme: '"error message"'
2025-09-03 15:02:28,275 - INFO - Routing function 'continue_investigation' called. Current state: logs_found=True, investigation_step=2
2025-09-03 15:02:28,275 - INFO - Loop condition: Logs found, exiting.
2025-09-03 15:02:28,277 - INFO - Node 'finalize_investigation': Finalizing investigation.
Final Answer (Logs Found): Investigation completed: Relevant logs found.
2025-09-03 15:02:28,280 - INFO - Node 'initialize_investigation': Starting investigation for 'non_existent_log_pattern'
2025-09-03 15:02:28,281 - INFO - Node 'search_logs': Search step 0 for 'non_existent_log_pattern'
2025-09-03 15:02:28,281 - INFO - Outil 'SearchLogs' appelé pour le terme: 'non_existent_log_pattern'
2025-09-03 15:02:28,489 - INFO - HTTP Request: POST https://api.groq.com/openai/v1/chat/completions "HTTP/1.1 200 OK"
2025-09-03 15:02:28,492 - INFO - Routing function 'continue_investigation' called. Current state: logs_found=False, investigation_step=1
2025-09-03 15:02:28,493 - INFO - Loop condition: Continuing investigation (step 1/2).
2025-09-03 15:02:28,494 - INFO - Node 'search_logs': Search step 1 for '"log_pattern:*non_existent*"'
2025-09-03 15:02:28,494 - INFO - Outil 'SearchLogs' appelé pour le terme: '"log_pattern:*non_existent*"'
2025-09-03 15:02:28,648 - INFO - HTTP Request: POST https://api.groq.com/openai/v1/chat/completions "HTTP/1.1 200 OK"
2025-09-03 15:02:28,650 - INFO - Routing function 'continue_investigation' called. Current state: logs_found=False, investigation_step=2
2025-09-03 15:02:28,650 - INFO - Loop condition: Max attempts reached, exiting.
2025-09-03 15:02:28,650 - INFO - Node 'finalize_investigation': Finalizing investigation.
Final Answer (Logs Not Found): Investigation completed: No logs found after 2 attempts.
----------------------------------------------------------------

--- TEST : Human-in-the-Loop (Fix Approval Agent) ---
Agent proposes an action and implicitly awaits human approval (by ending the current invoke)...
2025-09-03 15:02:28,653 - INFO - Node 'propose_action': Action proposal.
2025-09-03 15:02:28,841 - INFO - HTTP Request: POST https://api.groq.com/openai/v1/chat/completions "HTTP/1.1 200 OK"
2025-09-03 15:02:28,843 - INFO - Node 'feedback_decision_node': Graph has reached decision point for human feedback. Current human_feedback: 
2025-09-03 15:02:28,843 - INFO - Routing function 'route_on_feedback' : human_feedback=
2025-09-03 15:02:28,844 - INFO - No human feedback received yet. Routing to 'await_and_end' to pause current invoke and await external update.
Agent proposed: 'Deploy a caching layer (e.g., Redis or Memcached) to store frequently accessed model outputs, reducing the number of requests to the ML scoring service.'
Graph has ended (implicitly paused) awaiting human approval.
Simulating human approval (Approved)...
2025-09-03 15:02:28,846 - INFO - Node 'propose_action': Action proposal.
2025-09-03 15:02:29,022 - INFO - HTTP Request: POST https://api.groq.com/openai/v1/chat/completions "HTTP/1.1 200 OK"
2025-09-03 15:02:29,027 - INFO - Node 'feedback_decision_node': Graph has reached decision point for human feedback. Current human_feedback: approved
2025-09-03 15:02:29,027 - INFO - Routing function 'route_on_feedback' : human_feedback=approved
2025-09-03 15:02:29,027 - INFO - Human feedback: Approved. Routing to apply_action.
2025-09-03 15:02:29,029 - INFO - Node 'apply_action': Applying approved action: 'Deploy a caching layer (e.g., Redis or Memcached) to store frequently accessed model outputs, reducing the number of requests to the ML scoring service.'
2025-09-03 15:02:29,029 - INFO - Outil 'ApplyFix' appelé avec le correctif: 'Deploy a caching layer (e.g., Redis or Memcached) to store frequently accessed model outputs, reducing the number of requests to the ML scoring service.'   
Final Answer (Human Approved): Action applied: Correctif appliqué: Action générique effectuée. Vérification des résultats.

Simulating human rejection (Rejected)...
2025-09-03 15:02:29,031 - INFO - Node 'propose_action': Action proposal.
2025-09-03 15:02:29,261 - INFO - HTTP Request: POST https://api.groq.com/openai/v1/chat/completions "HTTP/1.1 200 OK"
2025-09-03 15:02:29,263 - INFO - Node 'feedback_decision_node': Graph has reached decision point for human feedback. Current human_feedback: 
2025-09-03 15:02:29,264 - INFO - Routing function 'route_on_feedback' : human_feedback=
2025-09-03 15:02:29,264 - INFO - No human feedback received yet. Routing to 'await_and_end' to pause current invoke and await external update.
2025-09-03 15:02:29,266 - INFO - Node 'propose_action': Action proposal.
2025-09-03 15:02:29,446 - INFO - HTTP Request: POST https://api.groq.com/openai/v1/chat/completions "HTTP/1.1 200 OK"
2025-09-03 15:02:29,448 - INFO - Node 'feedback_decision_node': Graph has reached decision point for human feedback. Current human_feedback: rejected
2025-09-03 15:02:29,449 - INFO - Routing function 'route_on_feedback' : human_feedback=rejected
2025-09-03 15:02:29,449 - INFO - Human feedback: Rejected. Routing to reject_action.
2025-09-03 15:02:29,455 - INFO - Node 'reject_action': Action rejected by human.
Final Answer (Human Rejected): Action rejected by human. Feedback: rejected. End.
----------------------------------------------------------------
```
