import os
import logging

from dotenv import load_dotenv

from langchain import hub
from langchain_groq import ChatGroq
from langchain_core.tools import Tool
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain.agents import AgentExecutor, create_react_agent

from tools.calculator import Calculator, CalculatorInput

# logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Chargement des variables d'environnement ---
load_dotenv()

def main():
    # --- 1. Récupération de la clé API Groq ---
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        logger.error("La variable d'environnement GROQ_API_KEY n'est pas définie. Veuillez la configurer dans le fichier .env.")
        return

    # --- 2. Initialisation du client Groq LLM ---
    try:
        llm = ChatGroq(
            temperature=0.7,
            model_name="llama-3.1-8b-instant",
            groq_api_key=groq_api_key
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

    # --- 4. Chargement et configuration du prompt spécialisé pour l'agent (Pattern ReAct) ---
    try:
        with open("prompts/system_prompt.txt", "r", encoding="utf-8") as f:
            persona_and_rules = f.read().strip()
        logger.info("Prompt ReAct chargé depuis 'prompts/system_prompt.txt'.")
    except FileNotFoundError:
        logger.error("Le fichier 'prompts/system_prompt.txt' est introuvable. Assurez-vous qu'il existe.")
        return
    except Exception as e:
        logger.error(f"Erreur lors du chargement du prompt: {e}")
        return
    
    react_system_template = (
            f"{persona_and_rules}\n\n"
            "Tu as accès aux outils suivants:\n"
            "{tools}\n\n"
            "Utilise le format suivant pour répondre:\n\n"
            "Question: la question que tu dois résoudre\n"
            "Thought: tu dois toujours réfléchir à ce que tu dois faire, si l'un des outils peut t'aider à réondre à la question, fais le avec les champs suivants :\n"
            "Action: Le nom de l'outil à utiliser pour répondre à la question. Il doit être parmi [{tool_names}]. Une seule Action à la fois.\n"
            "Action Input: l'entrée de l'action, les arguments envoyés à l'outil, sans les guillemets.\n"
            "Observation: le résultat de l'action\n"
            "Ce cycle se répète jusqu'à ce que tu trouves la réponse finale...\n"
            "Thought: Une fois que tu as toutes les informations nécessaires, que tu as résolu la  et que tu n'as plus besoin d'appeler d'outils, tu peux fournir la réponse finale :\n"
            "Final Answer: la réponse finale à la question originale\n\n"
            "Commence toujours par ta \"Thought\"."

            "Remember, you do not always need to use tools. Do not provide information the user did not ask for.\n"
            "Question: {input}\n"
            "Thought: {agent_scratchpad}\n"
        )
    
    system_message_prompt = SystemMessagePromptTemplate.from_template(react_system_template)
    human_message_prompt = HumanMessagePromptTemplate.from_template("{input}\n{agent_scratchpad}")

    prompt = ChatPromptTemplate(
            messages=[system_message_prompt, human_message_prompt],
            input_variables=['agent_scratchpad', 'input', 'tools', 'tool_names']
        )
        
    logger.info("ChatPromptTemplate ReAct créé avec succès et contenu personnalisé.")

    # --- 5. Création de l'agent LangChain ---
    agent = create_react_agent(llm, tools, prompt)
    logger.info("Agent ReAct créé avec le LLM et l'outil Calculatrice.")

    # --- 6. Création de l'AgentExecutor ---
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True, handle_parsing_errors=True)
    logger.info("AgentExecutor créé. Prêt à invoquer l'agent.")

    # --- 7. Exécution de l'agent avec des questions axées sur les calculs ---
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
            response = agent_executor.invoke({"input": q})
            print(f"Réponse finale de l'agent: {response['output']}")
        except Exception as e:
            logger.error(f"Erreur lors de l'exécution de l'agent pour la question '{q}': {e}")
            print(f"L'agent a rencontré une erreur: {e}")
        print("---------------------------------")

    print("\n--- Fin des tests de l'agent ---")

if __name__ == "__main__":
    main()
