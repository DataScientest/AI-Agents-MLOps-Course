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
├── requirements.txt # Python dependencies
├── prompts/
│ └── system_prompt.txt # Custom system prompt for the Calculator Agent's persona
└── tools/
├── init.py
└── calculator.py # Implementation of the 'Calculatrice' tool with numexp
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
LANGCHAIN_PROJECT="Calculator Agent"
```

### 3. Build and Run

Use the provided `Makefile` for ease of use.

*   **Install dependencies & run the agent:**
    ```bash
    make
    ```
    This command will:
    1.  Create a virtual environment (`uv venv`).
    2.  Install dependencies from `requirements.txt` (`uv pip install -r requirements.txt`).
    3.  Activate the virtual environment.
    4.  Execute the main agent script (`python3 -m src.main`).

### 4. Observe with LangSmith (Recommended)

While the agent runs, open your browser and navigate to [https://smith.langchain.com/](https://smith.langchain.com/). Log in and find the project "MLOps Guard Agent - Chapter 1 (Calculator)" to observe the detailed traces of the agent's execution, including its thoughts, actions, and tool calls.

### 5. Expected Agent Output :

```bash
(AI-Agents-MLOps-Course) ➜  AI-Agents-MLOps-Course git:(chapter-1) ✗ python3 -m src.main
2025-09-02 17:35:57,666 - INFO - Client Groq LLM 'llama-3.1-8b-instant' initialisé avec succès.
2025-09-02 17:35:57,666 - INFO - 1 outils définis et prêts pour l'agent.
2025-09-02 17:35:57,672 - INFO - Prompt ReAct chargé depuis 'prompts/system_prompt.txt'.
2025-09-02 17:35:57,672 - INFO - ChatPromptTemplate ReAct créé avec succès et contenu personnalisé.
2025-09-02 17:35:57,673 - INFO - Agent ReAct créé avec le LLM et l'outil Calculatrice.
2025-09-02 17:35:57,674 - INFO - AgentExecutor créé. Prêt à invoquer l'agent.

--- Début des tests de l'agent (Calculatrice uniquement) ---

--- Question 1: Quelle est la racine carrée de 144 plus 5 ? ---


> Entering new AgentExecutor chain...
2025-09-02 17:35:58,132 - INFO - HTTP Request: POST https://api.groq.com/openai/v1/chat/completions "HTTP/1.1 200 OK"
Thought: Pour résoudre cette question, j'ai besoin de calculer la racine carrée de 144 puis d'ajouter 5 au résultat. 

Action: Calculatrice
Action Input: sqrt(144) + 5
2025-09-02 17:35:58,314 - INFO - Outil 'calculatrice' appelé avec l'expression: 'sqrt(144) + 5'
2025-09-02 17:35:58,316 - INFO - Résultat de l'expression 'sqrt(144) + 5': 17
2025-09-02 17:35:58,445 - INFO - HTTP Request: POST https://api.groq.com/openai/v1/chat/completions "HTTP/1.1 200 OK"

Final Answer: La racine carrée de 144 plus 5 est 17.0.

> Finished chain.
Réponse finale de l'agent: La racine carrée de 144 plus 5 est 17.0.
---------------------------------

--- Question 2: Calcule 15 * (3 + 7) / 2. ---


> Entering new AgentExecutor chain...
2025-09-02 17:35:59,011 - INFO - HTTP Request: POST https://api.groq.com/openai/v1/chat/completions "HTTP/1.1 200 OK"
Thought: Pour résoudre cette question, je peux utiliser l'outil Calculatrice pour effectuer l'opération mathématique demandée.

Action: Calculatrice
Action Input: 15 * (3 + 7) / 2
2025-09-02 17:35:59,236 - INFO - Outil 'calculatrice' appelé avec l'expression: '15 * (3 + 7) / 2'
2025-09-02 17:35:59,237 - INFO - Résultat de l'expression '15 * (3 + 7) / 2': 75.0
2025-09-02 17:35:59,366 - INFO - HTTP Request: POST https://api.groq.com/openai/v1/chat/completions "HTTP/1.1 200 OK"

Thought: L'outil Calculatrice a effectué l'opération mathématique demandée et a obtenu le résultat 75.0.

Final Answer: La réponse finale est 75.0.

> Finished chain.
Réponse finale de l'agent: La réponse finale est 75.0.
---------------------------------

--- Question 3: Combien font 789 - 123 ? ---


> Entering new AgentExecutor chain...
2025-09-02 17:35:59,644 - INFO - HTTP Request: POST https://api.groq.com/openai/v1/chat/completions "HTTP/1.1 200 OK"
Thought: Je pense que je peux résoudre ce calcul de manière simple, mais je vais tout de même vérifier avec l'outil Calculatrice pour m'assurer de la précision.

Action: Calculatrice
Action Input: 789 - 123
2025-09-02 17:35:59,843 - INFO - Outil 'calculatrice' appelé avec l'expression: '789 - 123'
2025-09-02 17:35:59,843 - INFO - Résultat de l'expression '789 - 123': 666
2025-09-02 17:35:59,976 - INFO - HTTP Request: POST https://api.groq.com/openai/v1/chat/completions "HTTP/1.1 200 OK"

Thought: C'est confirmé, l'outil Calculatrice a donné le même résultat que ma première estimation.

Final Answer: La réponse est 666.

> Finished chain.
Réponse finale de l'agent: La réponse est 666.
---------------------------------

--- Question 4: Quel est le résultat de (100 / 4) + (20 * 3) ? ---


> Entering new AgentExecutor chain...
2025-09-02 17:36:00,248 - INFO - HTTP Request: POST https://api.groq.com/openai/v1/chat/completions "HTTP/1.1 200 OK"
Thought: Cette question nécessite une opération arithmétique simple et un calcul de multiplication puis d'addition. Je peux utiliser l'outil Calculatrice pour résoudre cela.

Action: Calculatrice
Action Input: (100 / 4) + (20 * 3)
2025-09-02 17:36:00,455 - INFO - Outil 'calculatrice' appelé avec l'expression: '(100 / 4) + (20 * 3)'
2025-09-02 17:36:00,456 - INFO - Résultat de l'expression '(100 / 4) + (20 * 3)': 85.0
2025-09-02 17:36:00,578 - INFO - HTTP Request: POST https://api.groq.com/openai/v1/chat/completions "HTTP/1.1 200 OK"

Final Answer: The final answer is 85.0.

> Finished chain.
Réponse finale de l'agent: The final answer is 85.0.
---------------------------------

--- Question 5: Divise 1 par zéro. ---


> Entering new AgentExecutor chain...
2025-09-02 17:36:04,958 - INFO - HTTP Request: POST https://api.groq.com/openai/v1/chat/completions "HTTP/1.1 429 Too Many Requests"
2025-09-02 17:36:04,959 - INFO - Retrying request to /openai/v1/chat/completions in 6.000000 seconds
2025-09-02 17:36:11,105 - INFO - HTTP Request: POST https://api.groq.com/openai/v1/chat/completions "HTTP/1.1 200 OK"
Thought: La question demande une opération arithmétique simple, je peux utiliser l'outil Calculatrice pour effectuer la division.

Action: Calculatrice
Action Input: 1 / 0
2025-09-02 17:36:11,319 - INFO - Outil 'calculatrice' appelé avec l'expression: '1 / 0'
2025-09-02 17:36:11,319 - ERROR - Erreur : Division par zéro dans l'expression '1 / 0'.
2025-09-02 17:36:11,354 - INFO - HTTP Request: POST https://api.groq.com/openai/v1/chat/completions "HTTP/1.1 429 Too Many Requests"
2025-09-02 17:36:11,354 - INFO - Retrying request to /openai/v1/chat/completions in 7.000000 seconds
2025-09-02 17:36:18,591 - INFO - HTTP Request: POST https://api.groq.com/openai/v1/chat/completions "HTTP/1.1 200 OK"

Erreur mathématique : Division par zéro.Question: Divise 1 par zéro.
Thought: La question demande une opération arithmétique simple, mais comme j'ai déjà essayé de l'exécuter avec l'outil Calculatrice et que cela a généré une erreur, je vais informer l'utilisateur de cette limitation.

Final Answer: La division par zéro n'est pas définie en mathématiques et ne peut pas être effectuée.

> Finished chain.
Réponse finale de l'agent: La division par zéro n'est pas définie en mathématiques et ne peut pas être effectuée.
---------------------------------

--- Question 6: Est-ce que le ciel est bleu ? ---


> Entering new AgentExecutor chain...
2025-09-02 17:36:18,799 - INFO - HTTP Request: POST https://api.groq.com/openai/v1/chat/completions "HTTP/1.1 429 Too Many Requests"
2025-09-02 17:36:18,800 - INFO - Retrying request to /openai/v1/chat/completions in 5.000000 seconds
2025-09-02 17:36:23,987 - INFO - HTTP Request: POST https://api.groq.com/openai/v1/chat/completions "HTTP/1.1 200 OK"
Thought: La question n'est pas mathématique, donc je ne peux pas utiliser l'outil Calculatrice pour répondre. Je vais donc répondre directement en utilisant mon savoir.

Final Answer: Je ne peux pas fournir une réponse définitive à cette question, car la couleur du ciel peut varier en fonction de la situation et des conditions météorologiques. Cependant, dans la plupart des cas, le ciel est bien bleu.

> Finished chain.
Réponse finale de l'agent: Je ne peux pas fournir une réponse définitive à cette question, car la couleur du ciel peut varier en fonction de la situation et des conditions météorologiques. Cependant, dans la plupart des cas, le ciel est bien bleu.
---------------------------------

--- Fin des tests de l'agent ---
```
