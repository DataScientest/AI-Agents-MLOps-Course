import logging
import random

from pydantic import BaseModel, Field
from typing import Literal

logger = logging.getLogger(__name__)

# --- Outil 1: Simuler la récupération de métriques système ---
class GetSystemMetricsInput(BaseModel):
    """Schéma d'entrée pour l'outil GetSystemMetrics."""
    component: str = Field(description="Nom du composant système dont on veut les métriques, ex: 'CPU', 'Memory', 'Disk'.")

def get_system_metrics(component: str) -> str:
    """Simule la récupération de métriques pour un composant système donné."""
    logger.info(f"Outil 'GetSystemMetrics' appelé pour le composant: '{component}'")
    metrics = {
        "CPU": {"usage": f"{random.randint(10, 90)}%", "load_avg": f"{random.uniform(0.5, 5.0):.2f}"},
        "Memory": {"usage": f"{random.randint(30, 95)}%", "free_gb": f"{random.uniform(1.0, 16.0):.1f}GB"},
        "Disk": {"usage": f"{random.randint(20, 98)}%", "free_gb": f"{random.uniform(50.0, 500.0):.1f}GB"},
    }
    result = metrics.get(component, {"error": "Composant non trouvé ou métriques indisponibles."})
    logger.info(f"Métriques simulées pour '{component}': {result}")
    return str(result)

# --- Outil 2: Simuler la vérification de la gravité d'une alerte ---
class CheckAlertSeverityInput(BaseModel):
    """Schéma d'entrée pour l'outil CheckAlertSeverity."""
    alert_description: str = Field(description="Description textuelle de l'alerte à évaluer.")

def check_alert_severity(alert_description: str) -> Literal["critical", "medium", "low"]:
    """Simule la détermination de la gravité d'une alerte basée sur sa description."""
    logger.info(f"Outil 'CheckAlertSeverity' appelé pour l'alerte: '{alert_description}'")
    alert_description_lower = alert_description.lower()
    if "critical" in alert_description_lower or "panne" in alert_description_lower or "down" in alert_description_lower:
        return "critical"
    elif "warning" in alert_description_lower or "élevé" in alert_description_lower or "haute utilisation" in alert_description_lower:
        return "medium"
    else:
        return "low"

# --- Outil 3: Simuler la recherche de logs pour un terme donné ---
class SearchLogsInput(BaseModel):
    """Schéma d'entrée pour l'outil SearchLogs."""
    search_term: str = Field(description="Terme à rechercher dans les logs du système.")

def search_logs(search_term: str) -> str:
    """Simule la recherche de logs pour un terme donné et retourne un extrait ou "rien trouvé"."""
    logger.info(f"Outil 'SearchLogs' appelé pour le terme: '{search_term}'")
    # Simule qu'un terme est trouvé après un certain nombre d'appels ou aléatoirement
    if "error" in search_term.lower() and random.random() < 0.7: # 70% de chance de trouver une erreur
        return f"Log trouvé : Erreur critique détectée avec '{search_term}'. Redémarrage nécessaire."
    elif "timeout" in search_term.lower() and random.random() < 0.5:
            return f"Log trouvé : Timeout de connexion détecté pour '{search_term}'."
    else:
        return "Aucun log pertinent trouvé pour ce terme."

# --- Outil 4: Simuler l'application d'un correctif ---
class ApplyFixInput(BaseModel):
    """Schéma d'entrée pour l'outil ApplyFix."""
    proposed_fix: str = Field(description="Description du correctif à appliquer.")

def apply_fix(proposed_fix: str) -> str:
    """Simule l'application d'un correctif système."""
    logger.info(f"Outil 'ApplyFix' appelé avec le correctif: '{proposed_fix}'")
    if "redémarrage" in proposed_fix.lower():
        return "Correctif appliqué: Redémarrage du service demandé. Surveillance en cours."
    elif "mise à jour" in proposed_fix.lower():
        return "Correctif appliqué: Mise à jour de configuration déployée. Vérification des services."
    else:
        return "Correctif appliqué: Action générique effectuée. Vérification des résultats."

# --- Outil 5: Calculatrice ---
class CalculatorInput(BaseModel):
    """Schema pour l'entrée de l'outil Calculatrice."""
    expression: str = Field(
        description="L'expression mathématique à évaluer, par exemple: '2 + 2 * 3'. "
                    "Doit être une expression numérique valide."
    )

def Calculator(expression: str) -> str:
    """
    Exécute une expression mathématique simple et retourne le résultat.
    """
    logger.info(f"Outil 'calculatrice' appelé avec l'expression: '{expression}'")
    try:
        result = str(ne.evaluate(expression))
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