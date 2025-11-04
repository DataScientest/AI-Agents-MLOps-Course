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

```sh
AI-Agents-MLOps-Course/
├── src/
│   ├── main.py                    # Runs all 4 agent patterns
│   ├── state.py                   # Shared agent state definition
│   ├── agents/
│   │   ├── linear_agent.py        # Pattern 1: Graph wiring (imports nodes)
│   │   ├── conditional_agent.py   # Pattern 2: Graph wiring (imports nodes)
│   │   ├── loop_agent.py          # Pattern 3: Graph wiring (imports nodes)
│   │   └── human_in_loop_agent.py # Pattern 4: Graph wiring (imports nodes)
│   └── nodes/
│       ├── linear_agent/          # Node implementations for linear pattern
│       ├── conditional_agent/     # Node implementations for conditional pattern
│       ├── loop_agent/            # Node implementations for loop pattern
│       └── human_in_loop_agent/   # Node implementations for human-in-loop pattern
├── src/tools/
│   └── mlops_tools.py             # Simulated monitoring tools
└── requirements.txt
```

## How to Run the Project

This project uses `uv` for dependency management and `Makefile` for simplified commands.

### 0. First-Time Setup (Recommended)

**After cloning this repository, run this command once to enable automatic workspace cleanup:**

```bash
bash scripts/setup-git-hooks.sh
```

This installs a Git hook that automatically cleans your workspace when switching between chapter branches, while preserving your `.env` file and `en/` folder. This ensures a clean slate when moving between chapters.

### 1. Prerequisites

*   **Python 3.9+** installed.
*   **`uv` installed:** `pip install uv` (or use `pip` directly for dependency management).
*   **Git** installed.
*   **Groq API Key:** Obtain a key from [Groq Cloud](https://console.groq.com/keys) and add it to your `.env` file.
*   **LangSmith API Key (Recommended for observability):** Obtain a key from [LangSmith](https://smith.langchain.com/) and add it to your `.env` file.

### 2. Setup (`.env` file)

Create a `.env` file at the root of the project :

```txt
GROQ_API_KEY="your_groq_api_key_here"
LANGCHAIN_TRACING_V2="true"
LANGCHAIN_API_KEY="your_langsmith_api_key_here"
LANGCHAIN_PROJECT="MLOps Guard Agent - Chapter 2 (LangGraph Patterns)"
```

### 3. Build and Run

Use the provided `Makefile` for ease of use.

1. Sync the virtual environment with `uv sync`.
2. Run the agents with `make demo`.

### 4. Observe with LangSmith (Recommended)

While the agents run, open your browser and navigate to [https://smith.langchain.com/](https://smith.langchain.com/). Log in and find the project "MLOps Guard Agent - Chapter 2 (LangGraph Patterns)" to observe the detailed traces of each agent's execution. Pay special attention to the visual graph view for each pattern, showing the nodes, edges, and state transitions.

### 5. Expected Agents Output

```sh
======================================================================
LangGraph Agent Patterns - Chapter 2 Demo
======================================================================
2025-10-23 14:55:34,247 - __main__ - INFO - ✓ LLM initialized: llama-3.1-8b-instant

======================================================================
PATTERN 0: Linear Workflow (Health Report Agent)
======================================================================
2025-10-23 14:55:34,313 - src.nodes.linear_agent.get_cpu_metrics - INFO - Node 'get_cpu_metrics' : Fetching CPU metrics.
2025-10-23 14:55:34,314 - src.tools.mlops_tools - INFO - Tool 'GetSystemMetrics' called for component: 'CPU'
2025-10-23 14:55:34,314 - src.tools.mlops_tools - INFO - Simulated metrics for 'CPU': {'usage': '15%', 'load_avg': '1.31'}
2025-10-23 14:55:34,314 - src.nodes.linear_agent.generate_report - INFO - Node 'generate_report' : Generating health report.
2025-10-23 14:55:34,568 - httpx - INFO - HTTP Request: POST https://api.groq.com/openai/v1/chat/completions "HTTP/1.1 200 OK"
2025-10-23 14:55:34,587 - src.nodes.linear_agent.finalize_report - INFO - Node 'finalize_report': Report finalized.

✓ Result: CPU health report completed. Content: **System Health Report**

**CPU Metrics:**

- **Usage:** 15% (within normal range)
- **Load Average:** 1.31 (within normal range)

**Health Status:** Normal

The system's CPU usage and load average are within normal limits, indicating stable system performance.
----------------------------------------------------------------------

======================================================================
PATTERN 1: Conditional Branching (Alert Router Agent)
======================================================================

[Test 1: Critical Alert]
2025-10-23 14:55:34,598 - src.nodes.conditional_agent.evaluate_alert - INFO - Node 'evaluate_alert': Evaluating alert: Critical service outage on production server!
2025-10-23 14:55:34,598 - src.tools.mlops_tools - INFO - Tool 'CheckAlertSeverity' called for alert: 'Critical service outage on production server!'
2025-10-23 14:55:34,598 - src.nodes.conditional_agent.evaluate_alert - INFO - Detected alert severity: critical
2025-10-23 14:55:34,599 - src.nodes.conditional_agent.routing - INFO - Routing alert based on severity: critical
2025-10-23 14:55:34,600 - src.nodes.conditional_agent.handle_critical - INFO - Node 'handle_critical_alert': Critical alert (Critical service outage on production server!). Immediate escalation.
✓ Result: CRITICAL alert detected. Immediate escalation to on-call pager.

[Test 2: Medium Alert]
2025-10-23 14:55:34,603 - src.nodes.conditional_agent.evaluate_alert - INFO - Node 'evaluate_alert': Evaluating alert: High CPU usage on ML analysis service.
2025-10-23 14:55:34,603 - src.tools.mlops_tools - INFO - Tool 'CheckAlertSeverity' called for alert: 'High CPU usage on ML analysis service.'
2025-10-23 14:55:34,603 - src.nodes.conditional_agent.evaluate_alert - INFO - Detected alert severity: medium
2025-10-23 14:55:34,603 - src.nodes.conditional_agent.routing - INFO - Routing alert based on severity: medium
2025-10-23 14:55:34,604 - src.nodes.conditional_agent.handle_medium - INFO - Node 'handle_medium_alert': Medium alert (High CPU usage on ML analysis service.). Launching auto-diagnosis.
✓ Result: MEDIUM alert detected. Starting automatic diagnosis.
----------------------------------------------------------------------

======================================================================
PATTERN 2: Loop with Conditions (Log Investigator Agent)
======================================================================

[Test 1: Search for 'error' logs]
2025-10-23 14:55:34,609 - src.nodes.loop_agent.initialize_investigation - INFO - Node 'initialize_investigation': Starting investigation for 'error'
2025-10-23 14:55:34,610 - src.nodes.loop_agent.search_logs - INFO - Node 'search_logs': Search step 0 for 'error'
2025-10-23 14:55:34,610 - src.tools.mlops_tools - INFO - Tool 'SearchLogs' called for term: 'error'
2025-10-23 14:55:34,745 - httpx - INFO - HTTP Request: POST https://api.groq.com/openai/v1/chat/completions "HTTP/1.1 200 OK"
2025-10-23 14:55:34,749 - src.nodes.loop_agent.routing - INFO - Routing function 'continue_investigation' called. Current state: logs_found=False, investigation_step=1
2025-10-23 14:55:34,749 - src.nodes.loop_agent.routing - INFO - Loop condition: Continuing investigation (step 1/5).
2025-10-23 14:55:34,752 - src.nodes.loop_agent.search_logs - INFO - Node 'search_logs': Search step 1 for '"error message"'
2025-10-23 14:55:34,753 - src.tools.mlops_tools - INFO - Tool 'SearchLogs' called for term: '"error message"'
2025-10-23 14:55:34,922 - httpx - INFO - HTTP Request: POST https://api.groq.com/openai/v1/chat/completions "HTTP/1.1 200 OK"
2025-10-23 14:55:34,924 - src.nodes.loop_agent.routing - INFO - Routing function 'continue_investigation' called. Current state: logs_found=False, investigation_step=2
2025-10-23 14:55:34,924 - src.nodes.loop_agent.routing - INFO - Loop condition: Continuing investigation (step 2/5).
2025-10-23 14:55:34,925 - src.nodes.loop_agent.search_logs - INFO - Node 'search_logs': Search step 2 for '"error messages"'
2025-10-23 14:55:34,925 - src.tools.mlops_tools - INFO - Tool 'SearchLogs' called for term: '"error messages"'
2025-10-23 14:55:35,072 - httpx - INFO - HTTP Request: POST https://api.groq.com/openai/v1/chat/completions "HTTP/1.1 200 OK"
2025-10-23 14:55:35,077 - src.nodes.loop_agent.routing - INFO - Routing function 'continue_investigation' called. Current state: logs_found=False, investigation_step=3
2025-10-23 14:55:35,077 - src.nodes.loop_agent.routing - INFO - Loop condition: Continuing investigation (step 3/5).
2025-10-23 14:55:35,080 - src.nodes.loop_agent.search_logs - INFO - Node 'search_logs': Search step 3 for '"error messages in"'
2025-10-23 14:55:35,080 - src.tools.mlops_tools - INFO - Tool 'SearchLogs' called for term: '"error messages in"'
2025-10-23 14:55:35,217 - httpx - INFO - HTTP Request: POST https://api.groq.com/openai/v1/chat/completions "HTTP/1.1 200 OK"
2025-10-23 14:55:35,221 - src.nodes.loop_agent.routing - INFO - Routing function 'continue_investigation' called. Current state: logs_found=False, investigation_step=4
2025-10-23 14:55:35,221 - src.nodes.loop_agent.routing - INFO - Loop condition: Continuing investigation (step 4/5).
2025-10-23 14:55:35,224 - src.nodes.loop_agent.search_logs - INFO - Node 'search_logs': Search step 4 for '"error messages including"'
2025-10-23 14:55:35,224 - src.tools.mlops_tools - INFO - Tool 'SearchLogs' called for term: '"error messages including"'
2025-10-23 14:55:35,365 - httpx - INFO - HTTP Request: POST https://api.groq.com/openai/v1/chat/completions "HTTP/1.1 200 OK"
2025-10-23 14:55:35,367 - src.nodes.loop_agent.routing - INFO - Routing function 'continue_investigation' called. Current state: logs_found=False, investigation_step=5
2025-10-23 14:55:35,367 - src.nodes.loop_agent.routing - INFO - Loop condition: Max attempts reached, exiting.
2025-10-23 14:55:35,369 - src.nodes.loop_agent.finalize_investigation - INFO - Node 'finalize_investigation': Finalizing investigation.
✓ Result: Investigation completed: No logs found after 5 attempts.

[Test 2: Search for non-existent pattern]
2025-10-23 14:55:35,373 - src.nodes.loop_agent.initialize_investigation - INFO - Node 'initialize_investigation': Starting investigation for 'non_existent_log_pattern'
2025-10-23 14:55:35,374 - src.nodes.loop_agent.search_logs - INFO - Node 'search_logs': Search step 0 for 'non_existent_log_pattern'
2025-10-23 14:55:35,374 - src.tools.mlops_tools - INFO - Tool 'SearchLogs' called for term: 'non_existent_log_pattern'
2025-10-23 14:55:35,529 - httpx - INFO - HTTP Request: POST https://api.groq.com/openai/v1/chat/completions "HTTP/1.1 200 OK"
2025-10-23 14:55:35,533 - src.nodes.loop_agent.routing - INFO - Routing function 'continue_investigation' called. Current state: logs_found=False, investigation_step=1
2025-10-23 14:55:35,533 - src.nodes.loop_agent.routing - INFO - Loop condition: Continuing investigation (step 1/2).
2025-10-23 14:55:35,535 - src.nodes.loop_agent.search_logs - INFO - Node 'search_logs': Search step 1 for '"log_pattern:*non_existent*"'
2025-10-23 14:55:35,536 - src.tools.mlops_tools - INFO - Tool 'SearchLogs' called for term: '"log_pattern:*non_existent*"'
2025-10-23 14:55:35,702 - httpx - INFO - HTTP Request: POST https://api.groq.com/openai/v1/chat/completions "HTTP/1.1 200 OK"
2025-10-23 14:55:35,706 - src.nodes.loop_agent.routing - INFO - Routing function 'continue_investigation' called. Current state: logs_found=False, investigation_step=2
2025-10-23 14:55:35,706 - src.nodes.loop_agent.routing - INFO - Loop condition: Max attempts reached, exiting.
2025-10-23 14:55:35,708 - src.nodes.loop_agent.finalize_investigation - INFO - Node 'finalize_investigation': Finalizing investigation.
✓ Result: Investigation completed: No logs found after 2 attempts.
----------------------------------------------------------------------

======================================================================
PATTERN 3: Human-in-the-Loop (Fix Approval Agent)
======================================================================

[Step 1: Agent proposes action]
2025-10-23 14:55:35,717 - src.nodes.human_in_loop_agent.propose_action - INFO - Node 'propose_action': Action proposal.
2025-10-23 14:55:35,899 - httpx - INFO - HTTP Request: POST https://api.groq.com/openai/v1/chat/completions "HTTP/1.1 200 OK"
2025-10-23 14:55:35,902 - src.nodes.human_in_loop_agent.feedback_decision - INFO - Node 'feedback_decision_node': Graph has reached decision point for human feedback. Current human_feedback: 
2025-10-23 14:55:35,903 - src.nodes.human_in_loop_agent.routing - INFO - Routing function 'route_on_feedback' : human_feedback=
2025-10-23 14:55:35,903 - src.nodes.human_in_loop_agent.routing - INFO - No human feedback received yet. Routing to 'await_and_end' to pause current invoke and await external update.
Proposed action: Deploy a caching layer (e.g., Redis or Memcached) to store frequently accessed model outputs, reducing the number of requests to the ML scoring service.
⏸️  Graph paused, awaiting human approval...

[Step 2: Human approves action]
2025-10-23 14:55:35,906 - src.nodes.human_in_loop_agent.propose_action - INFO - Node 'propose_action': Action proposal.
2025-10-23 14:55:36,080 - httpx - INFO - HTTP Request: POST https://api.groq.com/openai/v1/chat/completions "HTTP/1.1 200 OK"
2025-10-23 14:55:36,084 - src.nodes.human_in_loop_agent.feedback_decision - INFO - Node 'feedback_decision_node': Graph has reached decision point for human feedback. Current human_feedback: approved
2025-10-23 14:55:36,085 - src.nodes.human_in_loop_agent.routing - INFO - Routing function 'route_on_feedback' : human_feedback=approved
2025-10-23 14:55:36,085 - src.nodes.human_in_loop_agent.routing - INFO - Human feedback: Approved. Routing to apply_action.
2025-10-23 14:55:36,088 - src.nodes.human_in_loop_agent.apply_action - INFO - Node 'apply_action': Applying approved action: 'Deploy a caching layer (e.g., Redis or Memcached) to store frequently accessed model outputs, reducing the number of requests to the ML scoring service.'
2025-10-23 14:55:36,088 - src.tools.mlops_tools - INFO - Tool 'ApplyFix' called with fix: 'Deploy a caching layer (e.g., Redis or Memcached) to store frequently accessed model outputs, reducing the number of requests to the ML scoring service.'
✓ Result (Approved): Action applied: Fix applied: Generic action completed. Verifying results.

[Step 3: Testing rejection path]
2025-10-23 14:55:36,092 - src.nodes.human_in_loop_agent.propose_action - INFO - Node 'propose_action': Action proposal.
2025-10-23 14:55:36,273 - httpx - INFO - HTTP Request: POST https://api.groq.com/openai/v1/chat/completions "HTTP/1.1 200 OK"
2025-10-23 14:55:36,277 - src.nodes.human_in_loop_agent.feedback_decision - INFO - Node 'feedback_decision_node': Graph has reached decision point for human feedback. Current human_feedback: 
2025-10-23 14:55:36,278 - src.nodes.human_in_loop_agent.routing - INFO - Routing function 'route_on_feedback' : human_feedback=
2025-10-23 14:55:36,278 - src.nodes.human_in_loop_agent.routing - INFO - No human feedback received yet. Routing to 'await_and_end' to pause current invoke and await external update.
2025-10-23 14:55:36,282 - src.nodes.human_in_loop_agent.propose_action - INFO - Node 'propose_action': Action proposal.
2025-10-23 14:55:36,466 - httpx - INFO - HTTP Request: POST https://api.groq.com/openai/v1/chat/completions "HTTP/1.1 200 OK"
2025-10-23 14:55:36,471 - src.nodes.human_in_loop_agent.feedback_decision - INFO - Node 'feedback_decision_node': Graph has reached decision point for human feedback. Current human_feedback: rejected
2025-10-23 14:55:36,472 - src.nodes.human_in_loop_agent.routing - INFO - Routing function 'route_on_feedback' : human_feedback=rejected
2025-10-23 14:55:36,472 - src.nodes.human_in_loop_agent.routing - INFO - Human feedback: Rejected. Routing to reject_action.
2025-10-23 14:55:36,475 - src.nodes.human_in_loop_agent.reject_action - INFO - Node 'reject_action': Action rejected by human.
✓ Result (Rejected): Action rejected by human. Feedback: rejected. End.
----------------------------------------------------------------------

======================================================================
✓ Demo completed successfully!
======================================================================
```
