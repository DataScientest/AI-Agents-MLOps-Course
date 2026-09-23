# Rapport de migration : LangChain 1.x / LangGraph 1.x et modèles actuels

Repo : `DataScientest/AI-Agents-MLOps-Course`. Cours associé : *Patterns agentiques et monitoring* (`Learn_Content`, FR `patterns_agentiques_fr`, EN `agentic_patterns_en`).
Date : 2026-09-23. Ce même fichier figure sur chaque branche `feature/no-ref/langchain-v1-alignment-chapter-N`.

## Organisation des PR

Le repo a une branche de code par chapitre (`chapter-1` à `chapter-7`), donc une PR par branche de chapitre :

| Branche de travail | Cible |
|---|---|
| `feature/no-ref/langchain-v1-alignment-chapter-1` | `chapter-1` |
| `feature/no-ref/langchain-v1-alignment-chapter-2` | `chapter-2` |
| `feature/no-ref/langchain-v1-alignment-chapter-3` | `chapter-3` |
| `feature/no-ref/langchain-v1-alignment-chapter-4` | `chapter-4` |
| `feature/no-ref/langchain-v1-alignment-chapter-5` | `chapter-5` |
| `feature/no-ref/langchain-v1-alignment-chapter-6` | `chapter-6` |
| `feature/no-ref/langchain-v1-alignment-chapter-7` | `chapter-7` |

`chapter-6` et `chapter-7` pointaient sur le même commit (`2fe675b`). Les branches de travail 6 et 7 portent donc le même commit.

## Versions

Choix validé : garder la pile déjà en place (et validée de bout en bout par l'auteur en août 2026), sans montée de version. Seuls les écarts ont été corrigés.

| Paquet | Avant | Après | Dernière stable PyPI (23/09/2026) |
|---|---|---|---|
| langchain | 1.3.9 (pyproject) / **0.3.27** (requirements ch1, ch2, image agent ch3) | 1.3.9 partout | 1.4.2 |
| langchain-core | 1.4.7 / **0.3.74** (mêmes fichiers) | 1.4.7 partout | 1.6.4 |
| langgraph | 1.2.5 / **0.6.6** (mêmes fichiers) | 1.2.5 partout | 1.2.12 |
| langchain-groq | 1.1.3 / **0.3.7** (mêmes fichiers) | 1.1.3 partout | 1.1.3 |
| langchain-openai | `>=1.3.2` (pyproject ch1-3), `==1.3.2` (ch4-7) | `==1.3.2` partout | 1.6.4 |
| langgraph-checkpoint-postgres | 3.1.0 (ch4-7) | inchangé | 3.1.2 |
| langchain-huggingface | 1.2.2 (ch4-7) | inchangé | 1.2.2 |
| pytest (dev) | `>=8.4.2` (ch2, ch3), absent (ch1) | `==9.1.1` | 9.1.1 |
| langchain-community, langsmith | non utilisés en dépendance directe | – | 0.4.2 / 0.14.0 |
| SDK MCP (`mcp`) | non utilisé | non utilisé | 2.2.0 |

Inventaire des fichiers de dépendances avant migration :

| Branche | pyproject + uv.lock | requirements.txt | Utilisé par |
|---|---|---|---|
| chapter-1 | oui (1.x) | racine, **0.3.27** | Makefile `all:` (`uv pip install -r requirements.txt`) : la cible installait l'ancienne pile |
| chapter-2 | oui (1.x) | racine, **0.3.27** | rien |
| chapter-3 | oui (1.x) | `src/aiops_agent_monitor/requirements.txt` **0.3.27** + requirements des autres services | Dockerfile de l'Agent Core : **le conteneur tournait en LangChain 0.3** |
| chapter-4 à 7 | non | requirements par service, 1.x | Dockerfiles |

## Modifications par branche

### chapter-1
- `src/main.py` : `langgraph.prebuilt.create_react_agent(llm, tools, prompt=...)` devient `langchain.agents.create_agent(llm, tools, system_prompt=...)`. Modèle lu dans `GROQ_MODEL_NAME` (par défaut `openai/gpt-oss-20b`) et endpoint dans `LLM_API_BASE` (par défaut Groq).
- `requirements.txt` supprimé. `Makefile` : `all:` fait `uv sync` puis `uv run python -m src.main`, et une cible `test` est ajoutée.
- `pyproject.toml` : `langchain-openai==1.3.2`, groupe dev `pytest==9.1.1`, configuration pytest (marqueur `live`). `uv.lock` régénéré (voir « Points ouverts »).
- `.env.example` : `GROQ_MODEL_NAME`. `README.md` : arborescence, étapes `make`, prérequis Python 3.13, sortie attendue réécrite pour `create_agent`. `__pycache__` commités retirés de l'index.
- `tests/` : nouvelle suite.

### chapter-2
- `src/agents/agent_nodes.py` : `create_react_agent` devient `create_agent(system_prompt=...)`. Cette fabrique n'est appelée nulle part (code mort), mais elle est migrée pour ne plus exposer l'API dépréciée.
- `src/main.py` : `ChatGroq(model_name=os.getenv("GROQ_MODEL_NAME", "openai/gpt-oss-20b"))`.
- `requirements.txt` supprimé ; `pyproject.toml` épinglé ; `Makefile` : cible `test` activée ; `.env.example` et `README.md` mis à jour ; `.pyc` retirés de l'index.
- `tests/` : nouvelle suite. Attention : `tests/` est dans `.gitignore` sur cette branche, rubrique « Personal or sensitive files ». Les fichiers ont été ajoutés avec `git add -f` et la règle n'a pas été modifiée.

### chapter-3
- `src/aiops_agent_monitor/requirements.txt` (image Docker de l'Agent Core) passe de 0.3.27 / 0.6.6 / 0.3.7 à 1.3.9 / 1.4.7 / 1.2.5 / 1.1.3. Image reconstruite et vérifiée : versions 1.x installées, `import main` OK.
- Modèle par défaut `openai/gpt-oss-120b` dans `main.py` (sans valeur par défaut auparavant), `.env.example` (`llama-4-scout`), `README.md`, `docker-compose.yml` (`${GROQ_MODEL_NAME:-openai/gpt-oss-120b}`, car une variable vide rendait `os.getenv` inopérant) et `scripts/test_diagnostic_agent.py` (`llama-3.3-70b-versatile`).
- `pyproject.toml` épinglé ; `tests/` : nouvelle suite.

### chapter-4, chapter-5, chapter-6 (= chapter-7)
- Modèle Groq par défaut `openai/gpt-oss-120b` : `config.py` (`mixtral-8x7b-32768`), `main.py` (`llama-3.1-8b-instant`), `.env.example` et `README.md` (`llama-4-scout`), et en ch5-6 `knowledge_base_service/src/config.py`.
- Option d'embeddings OpenAI : `text-embedding-ada-002` devient `text-embedding-3-small` (1536 dimensions, documentation OpenAI). Commentaire `EMBEDDING_DIMENSIONS="1536"` avec rappel de passer la colonne pgvector `vector(384)` à `vector(1536)` dans `deployment/postgres/init.sql` (commentaire de ce fichier mis à jour). Le fournisseur par défaut reste TEI `BAAI/bge-small-en-v1.5` (384) : aucun schéma modifié.
- `Makefile` : cible `test-offline`. `tests/offline/` : nouvelle suite.
- ch6 uniquement : `tests/offline/test_mcp_agent.py`.

## APIs migrées

| Avant | Après | Où |
|---|---|---|
| `from langgraph.prebuilt import create_react_agent` / `create_react_agent(llm, tools, prompt=...)` | `from langchain.agents import create_agent` / `create_agent(llm, tools, system_prompt=...)` | ch1 `src/main.py`, ch2 `src/agents/agent_nodes.py` |
| Modèles Groq arrêtés (`llama-3.1-8b-instant` et `llama-3.3-70b-versatile` le 16/08/2026, `meta-llama/llama-4-scout-17b-16e-instruct` le 17/07/2026, `mixtral-8x7b-32768` le 20/03/2025) | `GROQ_MODEL_NAME`, par défaut `openai/gpt-oss-20b` (ch1-2, remplaçant officiel du 8B selon Groq) et `openai/gpt-oss-120b` (ch3+, déjà validé par l'auteur sur ch6) | toutes les branches |
| `text-embedding-ada-002` (option commentée) | `text-embedding-3-small` | ch4-7 |

`langgraph.prebuilt.ToolNode` est toujours d'actualité en 1.x : il est conservé dans les graphes personnalisés des chapitres 2 à 7.

## Chapitre 6 : MCP

- Le code correspond au texte : `src/tool_services/prometheus_tool/mcp_server.py` (`POST /mcp`, `tools/list` avec `ttlMs`/`cacheScope`, `tools/call`, erreurs de header `-32020`/400, méthode inconnue `-32601`/404), le client `src/aiops_agent_monitor/tools/mcp_client.py`, et la bascule `PROMETHEUS_TRANSPORT=http|mcp` dans `tools/mlops_tools.py` sans modification du graphe.
- **Aucun SDK MCP n'est utilisé** : le protocole (révision `2026-07-28`, HTTP sans état) est implémenté à la main (JSON-RPC 2.0 + `requests`/FastAPI). Le paquet `mcp` (2.2.0 sur PyPI) n'est pas une dépendance.
- Comme le signale le texte (ligne ~317 FR), `list_tools` existe dans le client, mais la découverte du catalogue n'est pas branchée dans le workflow de l'Agent Core : l'outil appelle directement `prometheus.query_range`. Rien n'a été changé.

## Tests exécutés

Tous les tests hors-ligne utilisent un modèle factice (`GenericFakeChatModel` dérivé pour accepter `bind_tools`) : aucune clé API n'est nécessaire.

| Branche | Commande | Contenu | Résultat |
|---|---|---|---|
| chapter-1 | `uv sync && uv run pytest` | agent `create_agent` réel : boucle ReAct avec outil, 2 branches (outil / réponse directe), boucle multi-outils avec arrêt, `recursion_limit`, HITL `HumanInTheLoopMiddleware` + `interrupt` repris par `Command(resume=...)`, `InMemorySaver` entre 2 appels, `src/main.py` de bout en bout | **7 passed**, 1 live désélectionné |
| chapter-2 | `uv sync && uv run pytest` | 4 patterns du cours : linéaire, conditionnel (critical/medium), boucle (conditions de sortie), HITL par drapeau d'état (approved/rejected), plus `interrupt()` + `Command(resume=...)`, checkpointer, `agent_nodes` sur `create_agent`, modèle via env | **13 passed**, 1 live désélectionné |
| chapter-3 | `uv sync && uv run pytest` | graphe de diagnostic réel : branche outil / directe, boucle outils, checkpointer, `interrupt` + `Command(resume=...)` | **5 passed**, 1 live désélectionné |
| chapter-3 | `docker build src/aiops_agent_monitor` + `import main` | image Agent Core | 1.x installé, import OK |
| chapter-4 | `make test-offline` | même suite, et `invoke(None, config)` comme `/resume_diagnosis` | **5 passed** |
| chapter-5 | `make test-offline` | idem | **5 passed** |
| chapter-6/7 | `make test-offline` | idem, plus l'agent qui appelle Prometheus via le client et le serveur MCP (en mémoire) et `list_tools` | **7 passed** |
| chapter-6/7 | `pytest tests/unit/test_mcp_endpoint.py` (existant) | serveur MCP | **6 passed** |
| chapter-6/7 | stack `make stop && make all`, `make status` | 7 services de la maille | tous `ok` |
| chapter-6/7 | curl exercice 1 (`tools/list`) du texte | catalogue `prometheus.query_range`, `ttlMs` 300000, `cacheScope` public | conforme |
| chapter-6/7 | curl exercice 2 (`tools/call`, requête `up`) | `isError: false`, séries `up` | conforme |
| chapter-6/7 | curl exercice 2 bis (header manquant) | HTTP 400 | conforme |
| chapter-6/7 | `pytest -m stack` (dans `tests/offline`) | agent (modèle factice) vers MCP vers la stack réelle | **1 passed** |
| chapter-6/7 | exercice 3 : `PROMETHEUS_TRANSPORT="mcp"`, `docker compose up -d --build aiops-agent-monitor`, `PrometheusQuery` invoqué dans le conteneur | log serveur `MCP tools/call prometheus.query_range` | conforme |

Tests `live` (vrai LLM) : écrits (`-m live`), **non exécutés** (voir ci-dessous).

## Points ouverts

1. **Tests live non exécutés.** Pas de clé Groq, et la clé fournie pour la gateway Liora (LiteLLM) est refusée : `LiteLLM Virtual Key expected ... expected to start with 'sk-'`. Pour la même raison, `make diagnose` (exercices 3 et 4 du chapitre 6) n'a pas été rejoué avec un vrai LLM. `openai/gpt-oss-20b` n'a donc pas été validé en réel sur ch1-2 (c'est un modèle de raisonnement : les réponses du chapitre 1 peuvent être plus longues).
2. **Bug préexistant au chapitre 2 (non corrigé, choix pédagogique)** : `search_logs_node` teste `"log trouvé" in search_result.lower()`, mais `search_logs` renvoie `"Found logs matching ..."`. `logs_found` reste donc toujours `False` et la boucle ne s'arrête que sur `max_investigation_steps`. La sortie montrée dans le cours (5 itérations avec `logs_found=False` pour « error ») reflète ce bug. Le corriger changerait la sortie attendue du chapitre.
3. **HITL du chapitre 2** : le cours enseigne une pause par drapeau d'état (`human_feedback` vide, puis `invoke` relancé avec l'état modifié), pas `interrupt()` / `Command(resume=...)`. Le code n'a pas été réécrit ; les primitives LangGraph 1.x sont testées à part.
4. **Repli OpenAI `gpt-4o-mini`** (ch4-7 `main.py`, `.env.example`, README), utilisé seulement sans clé Groq et sans `OPENAI_MODEL_NAME` : laissé en l'état. Le petit modèle actuellement recommandé par OpenAI, `gpt-6-luna`, ne fait du tool calling en Chat Completions qu'avec `reasoning_effort="none"`, donc un simple changement de nom casserait le diagnostic. À trancher.
5. **`uv.lock`** (ch1-3) : réécrit au format révision 3 par uv 0.12.18. Seul pytest change de version, mais le diff est volumineux.
6. Montée vers les dernières versions (langchain 1.4.2 / core 1.6.4 / langgraph 1.2.12 / openai 1.6.4) non faite, par choix. Elle impliquerait de reverrouiller ch1-3 et de régénérer les requirements Docker de ch4-7.
