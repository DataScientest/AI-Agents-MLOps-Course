import re
import numexpr as ne
import logging

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# --- 1.1. Définition du schéma d'entrée pour la calculatrice avec Pydantic ---
class CalculatorInput(BaseModel):
    """Schema pour l'entrée de l'outil Calculatrice."""
    expression: str = Field(
        description="L'expression mathématique à évaluer, par exemple: '2 + 2 * 3'. "
                    "Doit être une expression numérique valide."
    )

# --- 1.2. Fonction d'outil 'calculatrice' ---
def Calculator(expression: str) -> str:
    """
    Exécute une expression mathématique simple et retourne le résultat.
    AVERTISSEMENT : L'utilisation de eval() est dangereuse en production sans
    sandboxing strict. Pour cet exercice, nous allons nettoyer l'expression
    pour des raisons de sécurité de base, mais soyez conscient des risques.
    """

    logger.info(f"Outil 'calculatrice' appelé avec l'expression: '{expression}'")
    try:
        safe_expression = re.sub(r'[^-+*/(). \d]', '', expression)
        if not re.fullmatch(r'[\d\s+\-*/().]*', safe_expression):
            raise ValueError("Expression contient des caractères non autorisés.")

        result = str(ne.evaluate(safe_expression))
        logger.info(f"Résultat de l'expression '{expression}': {result}")
        return result
    except SyntaxError:
        logger.error(f"Erreur de syntaxe dans l'expression '{expression}'.")
        return "Erreur de syntaxe : L'expression mathématique est mal formée."
    except ZeroDivisionError:
        logger.error(f"Erreur : Division par zéro dans l'expression '{expression}'.")
        return "Erreur mathématique : Division par zéro."
    except Exception as e:
        logger.error(f"Erreur inattendue lors du calcul de l'expression '{expression}': {e}")
        return f"Erreur de calcul : {e}"
