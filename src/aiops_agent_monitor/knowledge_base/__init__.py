"""Knowledge Base module for RAG-powered incident retrieval."""

from .client import KnowledgeBaseClient, get_kb_client
from .models import Incident, DiagnosisFeedback, AlertTypeStats

__all__ = [
    "KnowledgeBaseClient",
    "get_kb_client",
    "Incident",
    "DiagnosisFeedback",
    "AlertTypeStats",
]
