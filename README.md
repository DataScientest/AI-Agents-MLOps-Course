# AI Agents MLOps Course - Chapter 1: Understanding AI Agents

This branch contains the completed practical exercise for Chapter 1, focusing on the fundamental differences between AI Agents and Chatbots, and the implementation of a basic ReAct agent with custom tools.

## Exercise Principle

In Chapter 1, students learn the core concepts of AI Agents (autonomy, statefulness, tool calling, ReAct pattern). This exercise provides a concrete example: a simple "Expert Calculator Agent". This agent demonstrates how a Large Language Model (LLM) can reason about a task, select the appropriate tool, execute it, observe the result, and use this feedback to generate a final answer.

## Project Structure

```
AI-Agents-MLOps-Course/
├── .env # Environment variables (GROQ_API_KEY, LangSmith config)
├── src/
│ ├── init.py
│ └── main.py # Main script: LLM setup, tool definition, agent creation, and test execution
├── pyproject.toml # Python dependencies (pinned, locked in uv.lock)
├── prompts/
│ └── system_prompt.txt # Custom system prompt for the Calculator Agent's persona
└── tools/
├── init.py
└── calculator.py # Implementation of the 'Calculatrice' tool with numexp
```

## How to Run the Project

This project uses `uv` for dependency management and `Makefile` for simplified commands.

### 0. First-Time Setup (Recommended)

**After cloning this repository, run this command once to enable automatic workspace cleanup:**

```bash
bash scripts/setup-git-hooks.sh
```

This installs a Git hook that automatically cleans untracked files when switching between chapter branches, while preserving your `.env` file, the `en/` and `docs/` folders and every git-ignored file (`.venv/`, `src/simple_chat.py`, ...). It only runs when the local branch is named exactly `chapter-N` (for example `git checkout chapter-1`). Commit or discard your changes to tracked files (such as `src/main.py`) before switching, otherwise git refuses the checkout.

### 1. Prerequisites

*   **Python 3.13+** installed (see `.python-version`).
*   **`uv` installed:** `pip install uv` (or use `pip` directly for dependency management).
*   **Git** installed.
*   **Groq API Key:** Obtain a key from [Groq Cloud](https://console.groq.com/keys) and add it to your `.env` file.
*   **LangSmith API Key (Recommended for observability):** Obtain a key from [LangSmith](https://smith.langchain.com/) and add it to your `.env` file.

### 2. Setup (`.env` file)

Create a `.env` file at the root of the project from the template, then fill in your key:
```bash
cp .env.example .env
```
```
GROQ_API_KEY="your_groq_api_key_here"
GROQ_MODEL_NAME="openai/gpt-oss-20b"
# Optional: any OpenAI-compatible endpoint (Groq by default)
# LLM_API_BASE="https://api.groq.com/openai/v1"

# Optional: LangSmith tracing
# LANGCHAIN_TRACING_V2="true"
# LANGCHAIN_API_KEY="your_langsmith_api_key_here"
# LANGCHAIN_PROJECT="AIOPS - Chapter 1"
# LANGCHAIN_ENDPOINT="https://api.smith.langchain.com"
```

### 3. Build and Run

Use the provided `Makefile` for ease of use.

*   **Install dependencies & run the agent:**
    ```bash
    make
    ```
    This command will:
    1.  Create the virtual environment and install the locked dependencies (`uv sync`).
    2.  Execute the main agent script (`uv run python -m src.main`).

### 4. Observe with LangSmith (Recommended)

While the agent runs, open your browser and navigate to [https://smith.langchain.com/](https://smith.langchain.com/). Log in and find the project "AIOPS - Chapter 1" to observe the detailed traces of the agent's execution, including its thoughts, actions, and tool calls.

### 5. Expected Agent Output :

```bash
$ uv run python -m src.main
... - INFO - Client Groq LLM 'openai/gpt-oss-20b' initialisé avec succès.
... - INFO - 1 outils définis et prêts pour l'agent.
... - INFO - Prompt système chargé depuis 'prompts/system_prompt.txt'.
... - INFO - Agent ReAct LangGraph créé avec le LLM et l'outil Calculatrice.

--- Début des tests de l'agent (Calculatrice uniquement) ---

--- Question 1: Quelle est la racine carrée de 144 plus 5 ? ---
... - INFO - Outil 'calculatrice' appelé avec l'expression: 'sqrt(144) + 5'
... - INFO - Résultat de l'expression 'sqrt(144) + 5': 17.0
Réponse finale de l'agent: La racine carrée de 144 plus 5 vaut **17**.
---------------------------------
...
--- Fin des tests de l'agent ---
```

Abridged: the agent is a LangGraph graph built by `langchain.agents.create_agent`, so the script prints the last message of the conversation instead of the old `Thought / Action / Observation` trace. The exact wording of the answers depends on the model.
