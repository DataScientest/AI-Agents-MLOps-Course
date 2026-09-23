# Rapport de migration : LangChain 1.x / LangGraph 1.x et modèles actuels

Repo : `DataScientest/AI-Agents-MLOps-Course`. Cours associé : *Patterns agentiques et monitoring* (`Learn_Content`, FR `patterns_agentiques_fr`, EN `agentic_patterns_en`). Repo d'examen : `DataScientest/AgenticDataAnalysis-Exam`.
Ce même fichier figure sur chaque branche `feature/no-ref/langchain-v1-alignment-chapter-N`.

## Organisation des PR

Une PR par branche de chapitre : `feature/no-ref/langchain-v1-alignment-chapter-N` → `chapter-N` (N = 1 à 7). `chapter-6` et `chapter-7` pointaient sur le même commit ; leurs branches de travail portent toujours le même commit.

Ordre de merge conseillé : repo d'examen, puis les 7 branches de pratique, puis `Learn_Content`.

## Versions

Pile conservée (déjà validée) et épinglée partout de la même façon :

| Paquet | Avant | Après |
|---|---|---|
| langchain / langchain-core / langgraph | 1.3.9 / 1.4.7 / 1.2.5 dans les pyproject, mais **0.3.27 / 0.3.74 / 0.6.6** dans les requirements de ch1, ch2 et de l'image Agent Core ch3 | 1.3.9 / 1.4.7 / 1.2.5 partout |
| langchain-openai | `>=1.3.2` (ch1-3), `==1.3.2` (ch4-7) | `==1.3.2` partout ; ajouté à l'image Agent Core ch3 |
| langchain-groq | 1.1.3 (et 0.3.7 dans les requirements obsolètes) | 1.1.3 (plus utilisé pour le LLM principal) |
| psycopg | `psycopg-binary==3.3.4` sans `psycopg` (ch4 : boucle de redémarrage), `psycopg[binary]>=3.3.0` (ch5), `psycopg[binary,pool]>=3.3.2` (ch6-7) | `psycopg[binary,pool]==3.3.6` + `psycopg-pool==3.3.3` partout (Agent Core, knowledge base, data loader) |
| pytest | `>=8.4.2` ou absent | `==9.1.1` ; ch7 : `tests/requirements.txt` épinglé |

Dernières versions PyPI au 23/09/2026, non adoptées par choix : langchain 1.4.2, langchain-core 1.6.4, langgraph 1.2.12, langchain-openai 1.6.4. SDK `mcp` 2.2.0 non utilisé : le chapitre 6 implémente MCP 2026-07-28 à la main.

## Modèle et configuration LLM

- Tous les chapitres utilisent `ChatOpenAI` sur l'API Groq compatible OpenAI : `GROQ_API_KEY`, `GROQ_MODEL_NAME`, et `LLM_API_BASE` (optionnel, Groq par défaut). Les chapitres 2 et 3, qui utilisaient `ChatGroq`, sont alignés sur ce schéma.
- Modèle par défaut : `openai/gpt-oss-20b` partout. Les anciens défauts étaient tous arrêtés chez Groq : `llama-3.1-8b-instant` et `llama-3.3-70b-versatile` le 16/08/2026, `llama-4-scout` le 17/07/2026, `mixtral-8x7b-32768` en 2025.
- Bug corrigé : avec une clé Groq, l'Agent Core (ch4-7) choisissait `OPENAI_API_BASE`, qui vaut `https://api.openai.com/v1` par défaut dans le compose, et **envoyait la clé Groq à OpenAI**. Une clé Groq va désormais vers `LLM_API_BASE`, sinon vers Groq.
- Embeddings (option OpenAI, ch4-7) : `text-embedding-ada-002` remplacé par `text-embedding-3-small` (1536 dimensions). Le défaut reste TEI `BAAI/bge-small-en-v1.5` (384).

## APIs migrées

| Avant | Après | Où |
|---|---|---|
| `langgraph.prebuilt.create_react_agent(llm, tools, prompt=...)` | `langchain.agents.create_agent(llm, tools, system_prompt=...)` | ch1 `src/main.py`, ch2 `src/agents/agent_nodes.py` |
| `ChatGroq(model_name=...)` | `ChatOpenAI(model=..., base_url=...)` | ch2, ch3 |
| `async def` + `.invoke()` synchrone (boucle d'événements bloquée) | `def` (threadpool FastAPI) | endpoints de diagnostic ch3-7, gateway ch5-7 |

## Garde-fous (ch3-7)

Ils sont nécessaires pour tenir dans l'offre gratuite de Groq (8 000 tokens/min, 200 000 tokens/jour). Avant, l'agent enchaînait 22 à 38 appels d'outils et dépassait le plafond sur une seule requête (413).

- `AGENT_RECURSION_LIMIT` (défaut **12**) : nombre d'étapes par diagnostic. À l'approche de la limite, l'agent rédige sa synthèse. La réponse est alors HTTP 200 avec `status: "degraded"` et `reason: "recursion_limit"`, jamais un 500.
- `TOOL_OUTPUT_MAX_CHARS` (défaut 2000) : les résultats d'outils (HTTP et MCP) sont tronqués, avec un marqueur.
- Mesures réelles avec `gpt-oss-20b` : une investigation courte consomme environ 7 200 tokens (5 s, `success`). Avec l'ancienne limite de 20 étapes, une investigation longue consommait 13 400 à 15 500 tokens : d'où le défaut de 12.

## Bugs corrigés (trouvés par le test apprenant de bout en bout)

- **ch1 :** `make run` passe par `uv run` (échouait dans un terminal neuf) ; test live robuste au format « 56 877 ».
- **ch2 :**
  - La boucle ne détectait jamais les logs trouvés (`"log trouvé"` comparé à une sortie en anglais).
  - Le HITL appliquait une autre action que celle approuvée : la reprise relançait `propose_action`. Désormais, une entrée conditionnelle depuis `START` reprend au point de décision.
  - Les nœuds dupliquaient l'historique des messages.
  - Les cibles `make` passent par `uv run`.
- **ch3-7 :**
  - La synthèse finale ne voyait jamais les résultats des outils ; elle les reçoit maintenant.
  - Un fingerprint réutilisé accumulait l'historique jusqu'au 413 permanent : seul le run courant est envoyé au LLM, et les checkpoints restent complets pour `/resume_diagnosis`.
  - Les 429/413 étaient avalés en « success » (ch6-7) : ils renvoient maintenant un HTTP 429 explicite.
  - Nouveau champ de réponse `tools_called`.
- **ch4-7 :**
  - Un feedback en double comptait deux fois : il renvoie maintenant 409.
  - Le pourcentage de succès s'affichait faux (`1/1 (0.0%)`) : corrigé dans `init.sql`.
  - ch5-7 : le feedback échouait en 500 (`datetime is not JSON serializable`) : corrigé.
- **Makefile :** `show-agent-steps` capture stderr ; les ports de `links` et `test-api` correspondent au compose.
- **ch7 :**
  - Collision des modules `tool` qui cassait `pytest tests/unit/` : corrigée par `tests/unit/conftest.py`.
  - Cibles `make test-unit`, `test-integration`, `test-e2e`, `test-chaos` et `test-sla`, avec `tests/requirements.txt`.
  - Les tests e2e et SLA exigent maintenant `status == "success"` et au moins un outil appelé.
- Nettoyage : `requirements.txt` obsolètes supprimés (ch1, ch2), `__pycache__` retirés de l'index, message du hook de nettoyage clarifié.

## Tests

| Branche | Commande | Résultat |
|---|---|---|
| chapter-1 | `uv run pytest` / `-m live` | 7 passed / 1 passed (Groq) |
| chapter-2 | `uv run pytest` / `-m live` | 15 passed / 1 passed |
| chapter-3 | `uv run pytest` | 14 passed |
| chapter-4, chapter-5 | `make test-offline` | 14 passed chacun |
| chapter-6/7 | `make test-offline` ; `make test-unit` | 18 passed ; 10 passed |
| chapter-6/7 (stack) | curl MCP des exercices 1 et 2, `pytest -m stack`, integration, e2e, SLA, chaos `test_circuit_breaker_prometheus_failure` (LLM factice compatible OpenAI) | conformes / passed |
| ch3, ch4, ch6 (stack, vrai Groq `gpt-oss-20b`) | un diagnostic réel chacun | aboutis, outils appelés, synthèse fondée sur les données |
| ch4 (stack) | agent stable avec Postgres, `/resume_diagnosis` | 0 redémarrage, checkpoints lus |

Les tests hors-ligne utilisent un modèle factice (`GenericFakeChatModel` dérivé pour accepter `bind_tools`) : aucune clé n'est nécessaire. Les tests live sont marqués `@pytest.mark.live`.

## Points ouverts

- `confidence_score` et `recommended_action` ne sont calculés sur aucune branche : ils valent toujours `null` et `"unknown"`. Le texte du cours le dit désormais. Les seuils `CONFIDENCE_THRESHOLD_*` de `.env.example` ne sont pas lus : le code utilise 0,90 / 0,70 en dur.
- ch7 : avec le quota gratuit et une limite de 12, une investigation longue finit en `degraded` et fait échouer e2e/SLA, qui exigent `success`. Le cours conseille `AGENT_RECURSION_LIMIT=20` et une pause entre les runs pour ces suites.
- `gpt-oss-20b` cherche parfois des métriques `container_*` absentes de la stack. Piste non appliquée : lister les métriques disponibles dans le prompt système.
- Les tests `-m live` et les diagnostics réels dépendent du quota Groq du jour (200 000 tokens par modèle et par organisation).
