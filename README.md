# AI Agents MLOps Course - Chapter 4: Intelligence and Memory

This branch provides the **completed solution** for Chapter 4. It focuses on endowing our MLOps Diagnostic Agent with **persistent session memory** using PostgreSQL checkpointing, making it a resilient and robust system.

## Exercise Principle

Chapter 4 introduces the concept of multi-level agent memory. This solution specifically demonstrates:
-   **Session Memory (Checkpoints):** Persistent storage of the agent's `AgentState` in PostgreSQL. This allows the agent to maintain its context and resume execution even after restarts or interruptions.
-   **Checkpointing with PostgreSQL:** Configuration of `PostgresSaver` with `ConnectionPool` to automatically save and load the agent's state for each diagnostic session (`thread_id`).
-   **Modular Architecture:** Clean separation of concerns with dedicated modules for nodes, agents, prompts, and tools (combining Chapter 3's structure with Chapter 4's memory features).
-   **Resilience:** The agent's diagnostic process is now resilient to service restarts, as its state is preserved in the database.

The goal is to provide a solid foundation for building intelligent agents that can manage long-running tasks and maintain context across invocations, which is critical for complex AIOps scenarios.

## Architecture Highlights

- **Modular Code Structure:** Separate `nodes/`, `agents/`, `prompts/`, and `tools/` modules for maintainability
- **PostgreSQL Checkpointing:** Uses `psycopg_pool.ConnectionPool` for efficient connection management
- **Production-Ready:** FastAPI application with proper connection pooling and error handling

## How to Set Up and Run the Solution

This project uses Docker Compose for service orchestration and a `Makefile` for simplified commands.

### 0. First-Time Setup (Recommended)

**After cloning this repository, run this command once to enable automatic workspace cleanup:**

```bash
bash scripts/setup-git-hooks.sh
```

This installs a Git hook that automatically cleans your workspace when switching between chapter branches, while preserving your `.env` file and `en/` folder. This ensures a clean slate when moving between chapters.

### 1. Prerequisites

*   **Python 3.9+** (for running `make` commands).
*   **Git** installed.
*   **Groq API Key:** Obtain a key from [Groq Cloud](https://console.groq.com/keys) and add it to your `.env` file.
*   **LangSmith API Key (Essential for observability):** Obtain a key from [LangSmith](https://smith.langchain.com/) and add it to your `.env` file.
*   **Docker & Docker Compose:** Essential for deploying the entire AIOps stack.

### 2. Setup (`.env` file)

Create a `.env` file at the root of the project. **Make sure your `GROQ_API_KEY` is correct.**


### 3. Deploy the AIOps Stack and Verify Checkpointing

This command will build all Docker images and deploy the entire AIOps stack, including PostgreSQL for checkpointing.

*   **From the project root, simply run:**
    ```bash
    make
    ```
    -   Verify all containers are running: `docker compose ps`.

*   **Test Checkpointing Activity:**
    1.  Trigger the agent with an alert:
        ```bash
        make trigger-alert-critical
        ```
    2.  **Inspect PostgreSQL for Checkpoint Data:**
        -   Access the PostgreSQL container shell: `docker exec -it postgres psql -U agent_user -d agent_checkpoints`
        -   List tables: `\dt` (you should see `langchain_checkpoint` and `langchain_thread`).
        -   Inspect `langchain_checkpoint` table: `SELECT thread_id, checkpoint_id, timestamp, state FROM langchain_checkpoint WHERE thread_id = 'alert_diagnosis_ch4_diag_alert_001';`
        -   You should see multiple rows for your `thread_id`, confirming that the agent's state is being saved.

### 4. Interact and Observe the Solution

*   **Access Monitoring Dashboards (Grafana)**
    Open your browser and navigate to `http://localhost:3001` (admin/admin).
    -   Explore the "News Classifier API Health Dashboard".
    -   Explore the "AIOps Monitor Agent Health Dashboard".
    -   Explore the "LangGraph Checkpoints - PostgreSQL Health" dashboard to see checkpoint activity.

*   **Observe Agent Logs (Docker)**
    ```bash
    docker logs aiops-agent-monitor
    ```
    You will see the agent receiving the alert, invoking LLM for decisions, calling `PrometheusQueryTool`, `LokiLogSearchTool`, and formulating a detailed diagnosis.

*   **Deep Dive with LangSmith (Essential)**
    Open your browser and navigate to [https://smith.langchain.com/](https://smith.langchain.com/). Log in and find the project "MLOps Guard Agent - Chapter 4 (Solution)".
    -   Click on a specific "Run" to view the execution flow.
    -   Check the PostgreSQL tables for checkpoint data to confirm persistence.

### 5. Testing PostgreSQL Memory/Checkpointing

To verify that the agent is using PostgreSQL for persistent memory:

**Step 1: Send an alert to the agent**
```bash
curl -X POST http://localhost:8005/diagnose_alert \
  -H "Content-Type: application/json" \
  -d '{
    "alerts": [{
      "labels": {"alertname": "HighCPUUsage", "service": "news-classifier-api"},
      "annotations": {"summary": "CPU usage above 80%"},
      "fingerprint": "test_memory_001"
    }]
  }'
```

**Step 2: Check PostgreSQL for checkpoints**
```bash
docker exec postgres psql -U agent_user -d agent_checkpoints -c \
  "SELECT COUNT(*) as checkpoint_count FROM checkpoints WHERE thread_id = 'alert_diagnosis_test_memory_001';"
```

You should see multiple checkpoints (typically 10+), confirming that each step of the agent's execution was persisted.

**Step 3: View checkpoint chain**
```bash
docker exec postgres psql -U agent_user -d agent_checkpoints -c \
  "SELECT checkpoint_id, parent_checkpoint_id FROM checkpoints WHERE thread_id = 'alert_diagnosis_test_memory_001' ORDER BY checkpoint_id LIMIT 5;"
```

This shows the parent-child relationship between checkpoints, demonstrating the execution flow.

**Step 4: Inspect checkpoint data**
```bash
docker exec postgres psql -U agent_user -d agent_checkpoints -c \
  "SELECT checkpoint_id, checkpoint->'channel_values'->>'messages' as messages FROM checkpoints WHERE thread_id = 'alert_diagnosis_test_memory_001' LIMIT 1;"
```

**What this demonstrates:**
- ✅ Each agent execution step creates a checkpoint in PostgreSQL
- ✅ The agent can resume from any checkpoint if interrupted
- ✅ Multiple invocations with the same `thread_id` maintain conversation history
- ✅ State is persisted even if the service restarts
- ✅ Uses ConnectionPool for efficient connection management

### 6. Management Commands

*   **Stop monitoring stack and services:**
    ```bash
    docker compose down
    ```
*   **View agent logs:**
    ```bash
    docker logs ai-agents-mlops-course-aiops-agent-monitor-1 -f
    ```
*   **Access PostgreSQL directly:**
    ```bash
    docker exec -it postgres psql -U agent_user -d agent_checkpoints
    ```
