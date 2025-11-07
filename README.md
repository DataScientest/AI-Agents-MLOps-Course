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
- **RAG with Knowledge Base:** Semantic search over past incidents using pgvector + TEI embeddings
- **Production-Ready:** FastAPI application with proper connection pooling and error handling

## 🚀 Quick Start (3 Commands)

```bash
# 1. Start all services
docker compose up --build -d

# 2. Load sample incidents for RAG (first time only)
docker compose --profile tools up data-loader

# 3. Test the agent with RAG
curl -X POST http://localhost:8005/diagnose_alert \
  -H "Content-Type: application/json" \
  -d '{
    "alerts": [{
      "labels": {"alertname": "HighCPUUsage", "service": "news-classifier-api"},
      "annotations": {"summary": "CPU spiking to 95% during deployment"},
      "fingerprint": "test_001"
    }]
  }' | jq -r '.agent_diagnosis'
```

**What happens:**
- ✅ Agent searches knowledge base for similar incidents (RAG)
- ✅ Finds INC-001 with same issue and solution
- ✅ Uses historical context to provide better diagnosis
- ✅ All steps saved as checkpoints in PostgreSQL

**Verify it worked:**
```bash
# Check RAG: Should show 20 incidents
docker exec postgres psql -U agent_user -d agent_checkpoints -c "SELECT COUNT(*) FROM incident_knowledge;"

# Check Memory: Should show 10+ checkpoints
docker exec postgres psql -U agent_user -d agent_checkpoints -c "SELECT COUNT(*) FROM checkpoints WHERE thread_id = 'alert_diagnosis_test_001';"

# Check logs: Should see "RAGKnowledgeSearch called" and "Found X similar incidents"
docker logs ai-agents-mlops-course-aiops-agent-monitor-1 2>&1 | grep -A 2 "RAGKnowledgeSearch"
```

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


### 3. Deploy the AIOps Stack

This command will build all Docker images and deploy the entire AIOps stack, including PostgreSQL for checkpointing and TEI for embeddings.

*   **From the project root, simply run:**
    ```bash
    make
    # OR
    docker compose up --build -d
    ```
    
*   **Verify all containers are running:**
    ```bash
    docker compose ps
    ```
    
    You should see: aiops-agent-monitor, postgres, tei, prometheus, grafana, loki, etc.

*   **Load sample incidents for RAG (first time only):**
    ```bash
    docker compose --profile tools up data-loader
    ```
    
    This loads 20 sample incidents with embeddings (~30 seconds). Only needs to run once.

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

### 5. Testing RAG (Retrieval-Augmented Generation) with Knowledge Base

The agent uses RAG to search for similar past incidents before diagnosing new alerts. This provides context-aware solutions based on historical data.

**🎯 What is RAG?**
- **R**etrieval: Search for similar past incidents using semantic similarity
- **A**ugmented: Enhance the agent's context with relevant historical data
- **G**eneration: Generate better diagnoses using both current data and past solutions

**Step 1: Load sample incidents (first time only)**

Load 20 sample incidents into the knowledge base:

```bash
docker compose --profile tools up data-loader
```

This runs a one-time data loader that:
- Waits for PostgreSQL and TEI to be ready
- Generates embeddings for each incident using TEI
- Stores them in PostgreSQL with pgvector
- Exits automatically when complete (~30 seconds)

Verify the data was loaded:

```bash
docker exec postgres psql -U agent_user -d agent_checkpoints -c \
  "SELECT COUNT(*) FROM incident_knowledge;"
```

You should see `20` incidents.

**Step 2: Send an alert and observe RAG in action**

```bash
curl -X POST http://localhost:8005/diagnose_alert \
  -H "Content-Type: application/json" \
  -d '{
    "alerts": [{
      "labels": {
        "alertname": "HighCPUUsage",
        "service": "news-classifier-api"
      },
      "annotations": {
        "summary": "CPU spiking to 95% during deployment"
      },
      "fingerprint": "test_rag_demo"
    }]
  }' | jq -r '.agent_diagnosis'
```

**Step 3: Check agent logs to see RAG tool usage**

```bash
docker logs ai-agents-mlops-course-aiops-agent-monitor-1 2>&1 | grep -A 3 "RAGKnowledgeSearch"
```

You should see:
- ✅ `RAGKnowledgeSearch called` with the query
- ✅ `Found X similar incidents` from the knowledge base
- ✅ The agent using historical solutions to inform its diagnosis

**Step 4: Query the knowledge base directly**

See what similar incidents exist:

```bash
docker exec postgres psql -U agent_user -d agent_checkpoints -c \
  "SELECT incident_id, service_name, alert_type, summary FROM incident_knowledge WHERE service_name = 'news-classifier-api' LIMIT 5;"
```

**Step 5: Test semantic search**

The embeddings enable semantic search (meaning-based, not just keyword matching):

```bash
# This will find incidents about CPU issues even if worded differently
curl -X POST http://localhost:8005/diagnose_alert \
  -H "Content-Type: application/json" \
  -d '{
    "alerts": [{
      "labels": {"alertname": "PerformanceIssue", "service": "news-classifier-api"},
      "annotations": {"summary": "Service running slow with high processor usage"},
      "fingerprint": "semantic_test"
    }]
  }' | jq -r '.agent_diagnosis'
```

**What this demonstrates:**
- ✅ Agent automatically searches knowledge base before diagnosing
- ✅ Semantic similarity finds relevant incidents (not just keyword matching)
- ✅ Past solutions inform current diagnosis
- ✅ Free HuggingFace TEI embeddings (no OpenAI cost!)
- ✅ PostgreSQL with pgvector for fast similarity search

### 6. Testing PostgreSQL Memory/Checkpointing

**Step 1: Send an alert**
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

You should see multiple checkpoints (typically 10+).

**Step 3: View checkpoint chain**
```bash
docker exec postgres psql -U agent_user -d agent_checkpoints -c \
  "SELECT checkpoint_id, parent_checkpoint_id FROM checkpoints WHERE thread_id = 'alert_diagnosis_test_memory_001' ORDER BY checkpoint_id LIMIT 5;"
```

**What this demonstrates:**
- ✅ Each agent execution step creates a checkpoint in PostgreSQL
- ✅ The agent can resume from any checkpoint if interrupted
- ✅ State is persisted even if the service restarts
- ✅ Uses ConnectionPool for efficient connection management

### 7. Management Commands

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
