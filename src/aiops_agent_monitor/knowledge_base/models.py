"""Data models for Knowledge Base entities."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class Incident(BaseModel):
    """Represents a past incident stored in knowledge base."""

    id: Optional[int] = None
    incident_id: str
    service_name: str
    alert_type: str
    severity: str

    summary: str
    root_cause: str
    solution: str

    occurred_at: datetime
    resolved_at: Optional[datetime] = None
    resolution_time_seconds: Optional[int] = None

    times_referenced: int = 0
    success_count: int = 0
    failure_count: int = 0
    confidence_score: float = 0.0

    embedding: Optional[List[float]] = None  # 1536-dim vector

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        from_attributes = True


class DiagnosisFeedback(BaseModel):
    """Represents feedback on an agent diagnosis."""

    id: Optional[int] = None
    diagnosis_id: str
    thread_id: str

    alert_info: str
    service_name: Optional[str] = None
    alert_type: Optional[str] = None

    proposed_root_cause: Optional[str] = None
    proposed_solution: Optional[str] = None
    confidence_score: Optional[float] = None

    outcome: Optional[str] = None  # success, partial_success, failure, escalated
    human_correction: Optional[str] = None
    corrected_root_cause: Optional[str] = None
    corrected_solution: Optional[str] = None

    diagnosed_at: datetime = Field(default_factory=datetime.now)
    feedback_received_at: Optional[datetime] = None

    incident_knowledge_id: Optional[int] = None

    class Config:
        from_attributes = True


class AlertTypeStats(BaseModel):
    """Statistics for a specific alert type (for confidence scoring)."""

    id: Optional[int] = None
    service_name: str
    alert_type: str

    total_diagnoses: int = 0
    successful_diagnoses: int = 0
    failed_diagnoses: int = 0
    escalated_diagnoses: int = 0

    avg_resolution_time_seconds: Optional[float] = None
    confidence_score: float = 0.0

    last_updated: datetime = Field(default_factory=datetime.now)

    class Config:
        from_attributes = True


class SimilarIncident(BaseModel):
    """Incident with similarity score (used in RAG retrieval)."""

    incident: Incident
    similarity_score: float

    def to_text_summary(self) -> str:
        """Convert to text summary for LLM context."""
        return f"""
Incident: {self.incident.incident_id} (Similarity: {self.similarity_score:.2f})
Service: {self.incident.service_name}
Alert Type: {self.incident.alert_type}
Severity: {self.incident.severity}
Summary: {self.incident.summary}
Root Cause: {self.incident.root_cause}
Solution: {self.incident.solution}
Success Rate: {self.incident.confidence_score:.1%} ({self.incident.success_count}/{self.incident.times_referenced} references)
""".strip()
