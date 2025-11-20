"""Confidence scoring and decision logic for the diagnostic agent.

This module implements the decision thresholds for the agent based on
historical confidence scores. It determines whether to auto-remediate,
suggest a solution, or escalate to a human.
"""

# Configuration - Tunable thresholds for agent behavior
CONFIDENCE_THRESHOLDS = {
    "auto_remediate": 0.90,  # 90% confidence required for auto-fix
    "suggest": 0.70,         # 70% confidence required for suggestion
    "escalate": 0.0          # Fallback - always escalate if below suggest
}


def get_recommendation(confidence_score: float, total_diagnoses: int) -> tuple[str, str]:
    """
    Determines the recommended action based on confidence score and history.
    
    Args:
        confidence_score: Historical success rate (0.0-1.0)
        total_diagnoses: Number of past diagnoses for this alert type
        
    Returns:
        Tuple of (action, reason) where action is one of:
        - "auto_remediate": Apply solution automatically
        - "suggest": Suggest solution to human
        - "escalate": Escalate to human for manual handling
    """
    # Not enough historical data
    if total_diagnoses < 3:
        return "escalate", f"Not enough data (need 3+ diagnoses, have {total_diagnoses})"
    
    # High confidence: Trust our past performance
    if confidence_score >= CONFIDENCE_THRESHOLDS["auto_remediate"]:
        return "auto_remediate", f"High confidence ({confidence_score:.1%}) - Safe to automate"
    
    # Medium confidence: Suggest but require approval
    if confidence_score >= CONFIDENCE_THRESHOLDS["suggest"]:
        return "suggest", f"Medium confidence ({confidence_score:.1%}) - Human review needed"
    
    # Low confidence: Ask for help
    return "escalate", f"Low confidence ({confidence_score:.1%}) - Escalate to human"
