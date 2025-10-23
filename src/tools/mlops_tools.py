import logging
import random

from pydantic import BaseModel, Field
from typing import Literal

logger = logging.getLogger(__name__)

# --- Tool 1: Simulate system metrics retrieval ---
class GetSystemMetricsInput(BaseModel):
    """Input schema for GetSystemMetrics tool."""
    component: str = Field(description="Name of the system component to get metrics for, e.g., 'CPU', 'Memory', 'Disk'.")

def get_system_metrics(component: str) -> str:
    """Simulate fetching metrics for a given system component."""
    logger.info(f"Tool 'GetSystemMetrics' called for component: '{component}'")
    metrics = {
        "CPU": {"usage": f"{random.randint(10, 90)}%", "load_avg": f"{random.uniform(0.5, 5.0):.2f}"},
        "Memory": {"usage": f"{random.randint(30, 95)}%", "free_gb": f"{random.uniform(1.0, 16.0):.1f}GB"},
        "Disk": {"usage": f"{random.randint(20, 98)}%", "free_gb": f"{random.uniform(50.0, 500.0):.1f}GB"},
    }
    result = metrics.get(component, {"error": "Component not found or metrics unavailable."})
    logger.info(f"Simulated metrics for '{component}': {result}")
    return str(result)

# --- Tool 2: Simulate alert severity check ---
class CheckAlertSeverityInput(BaseModel):
    """Input schema for CheckAlertSeverity tool."""
    alert_description: str = Field(description="Text description of the alert to evaluate.")

def check_alert_severity(alert_description: str) -> Literal["critical", "medium", "low"]:
    """Simulate determining alert severity based on its description."""
    logger.info(f"Tool 'CheckAlertSeverity' called for alert: '{alert_description}'")
    alert_description_lower = alert_description.lower()
    if "critical" in alert_description_lower or "outage" in alert_description_lower or "down" in alert_description_lower:
        return "critical"
    elif "warning" in alert_description_lower or "high" in alert_description_lower or "elevated" in alert_description_lower:
        return "medium"
    else:
        return "low"

# --- Tool 3: Simulate log search ---
class SearchLogsInput(BaseModel):
    """Input schema for SearchLogs tool."""
    search_term: str = Field(description="Term to search for in system logs.")

def search_logs(search_term: str) -> str:
    """Simulate searching logs for a given term and return an excerpt or 'nothing found'."""
    logger.info(f"Tool 'SearchLogs' called for term: '{search_term}'")
    # Simulate finding logs randomly
    if "error" in search_term.lower() and random.random() < 0.7:  # 70% chance of finding error
        return f"Found logs matching '{search_term}': Critical error detected. Restart required."
    elif "timeout" in search_term.lower() and random.random() < 0.5:
        return f"Found logs matching '{search_term}': Connection timeout detected."
    else:
        return f"No relevant logs found for term '{search_term}'."

# --- Tool 4: Simulate applying a fix ---
class ApplyFixInput(BaseModel):
    """Input schema for ApplyFix tool."""
    proposed_fix: str = Field(description="Description of the fix to apply.")

def apply_fix(proposed_fix: str) -> str:
    """Simulate applying a system fix."""
    logger.info(f"Tool 'ApplyFix' called with fix: '{proposed_fix}'")
    if "restart" in proposed_fix.lower():
        return "Fix applied: Service restart requested. Monitoring in progress."
    elif "update" in proposed_fix.lower():
        return "Fix applied: Configuration update deployed. Verifying services."
    else:
        return "Fix applied: Generic action completed. Verifying results."

# --- Tool 5: Calculator ---
class CalculatorInput(BaseModel):
    """Input schema for Calculator tool."""
    expression: str = Field(
        description="Mathematical expression to evaluate, e.g., '2 + 2 * 3'. "
                    "Must be a valid numeric expression."
    )

def Calculator(expression: str) -> str:
    """
    Execute a simple mathematical expression and return the result.
    """
    logger.info(f"Tool 'Calculator' called with expression: '{expression}'")
    try:
        import numexpr as ne
        result = str(ne.evaluate(expression))
        logger.info(f"Result of expression '{expression}': {result}")
        return result
    except SyntaxError:
        logger.error(f"Syntax error in expression '{expression}'.")
        return "Syntax error: Mathematical expression is malformed."
    except ZeroDivisionError:
        logger.error(f"Error: Division by zero in expression '{expression}'.")
        return "Math error: Division by zero."
    except Exception as e:
        logger.error(f"Unexpected error calculating expression '{expression}': {e}")
        return f"Calculation error: {e}"