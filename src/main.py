import os
import logging

from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.tools import Tool
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent

from tools.calculator import Calculator, CalculatorInput

# logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Chargement des variables d'environnement ---
load_dotenv(override=True)

def main():
    # --- 1. Récupération de la clé API Groq ---
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        logger.error("La variable d'environnement GROQ_API_KEY n'est pas définie. Veuillez la configurer dans le fichier .env.")
        return

    # --- 2. Initialisation du client Groq LLM via OpenAI-compatible endpoint ---
    try:
        llm = ChatOpenAI(
            model="llama-3.1-8b-instant",
            temperature=0.7,
            api_key=groq_api_key,
            base_url="https://api.groq.com/openai/v1"
        )
        logger.info(f"Client Groq LLM '{llm.model_name}' initialisé avec succès.")
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation du LLM Groq: {e}")
        return

    # --- 3. Définition des outils et messages à envoyer au LLM ---
    tools = [
        Tool(
            name="Calculatrice",
            func=Calculator,
            description=(
                "Utile pour effectuer des opérations arithmétiques et des fonctions mathématiques (ex: sqrt, log, sin). "
                "Prend une expression mathématique FORMELLE sous forme de chaîne de caractères, ex: '2 + 2 * 3' ou 'sqrt(144) + 5'."
                "N'utilise PAS de langage naturel pour décrire l'opération."
            ),
            args_schema=CalculatorInput
        )
    ]
    logger.info(f"{len(tools)} outils définis et prêts pour l'agent.")

    # --- 4. Chargement du prompt système (persona + règles métier) ---
    try:
        with open("prompts/system_prompt.txt", "r", encoding="utf-8") as f:
            system_prompt = f.read().strip()
        logger.info("Prompt système chargé depuis 'prompts/system_prompt.txt'.")
    except FileNotFoundError:
        logger.error("Le fichier 'prompts/system_prompt.txt' est introuvable. Assurez-vous qu'il existe.")
        return
    except Exception as e:
        logger.error(f"Erreur lors du chargement du prompt: {e}")
        return

    # --- 5. Création de l'agent ReAct (LangGraph) ---
    # create_react_agent retourne un graphe LangGraph compilé qui implémente
    # la boucle ReAct : Raisonner → Agir (appel d'outil) → Observer → Raisonner...
    agent = create_react_agent(llm, tools, prompt=system_prompt)
    logger.info("Agent ReAct LangGraph créé avec le LLM et l'outil Calculatrice.")

    # --- 6. Exécution de l'agent avec des questions axées sur les calculs ---
    questions = [
        "Quelle est la racine carrée de 144 plus 5 ?",
        "Calcule 15 * (3 + 7) / 2.",
        "Combien font 789 - 123 ?",
        "Quel est le résultat de (100 / 4) + (20 * 3) ?",
        "Divise 1 par zéro.", # Test de gestion d'erreur de l'outil
        "Est-ce que le ciel est bleu ?" # Test pour voir si l'agent tente d'utiliser la calculatrice
    ]

    print("\n--- Début des tests de l'agent (Calculatrice uniquement) ---")
    for i, q in enumerate(questions):
        print(f"\n--- Question {i+1}: {q} ---")
        try:
            result = agent.invoke({"messages": [HumanMessage(content=q)]})
            final_answer = result["messages"][-1].content
            print(f"Réponse finale de l'agent: {final_answer}")
        except Exception as e:
            logger.error(f"Erreur lors de l'exécution de l'agent pour la question '{q}': {e}")
            print(f"L'agent a rencontré une erreur: {e}")
        print("---------------------------------")

    print("\n--- Fin des tests de l'agent ---")

if __name__ == "__main__":
    main()
