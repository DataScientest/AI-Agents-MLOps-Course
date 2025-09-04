import logging

from pydantic import BaseModel, Field
from typing import Literal

logger = logging.getLogger(__name__)

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
