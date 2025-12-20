import logging
import requests
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any

from config import (
    POSTGRES_URI,
    DEPLOYMENT_MODE,
    KNOWLEDGE_BASE_URL,
    RAG_TOP_K,
    RAG_SIMILARITY_THRESHOLD,
)
from .models import Incident, SimilarIncident, DiagnosisFeedback, AlertTypeStats

logger = logging.getLogger(__name__)

class KnowledgeBaseClient(ABC):
    """Abstract base class for knowledge base access."""

    @abstractmethod
    def search_similar_incidents(self, query: str, **kwargs) -> List[SimilarIncident]: pass

    @abstractmethod
    def add_incident(self, incident: Incident) -> int: pass

    @abstractmethod
    def record_diagnosis_feedback(self, feedback: DiagnosisFeedback) -> int: pass

    @abstractmethod
    def get_alert_type_confidence(self, service_name: str, alert_type: str) -> Optional[AlertTypeStats]: pass

    @abstractmethod
    def update_incident_reference(self, incident_id: str, successful: bool) -> None: pass


class HTTPKnowledgeBaseClient(KnowledgeBaseClient):
    """HTTP-based knowledge base client for microservices deployment."""

    def __init__(self, service_url: str):
        self.service_url = service_url.rstrip('/')
        logger.info(f"Initialized HTTP KB client for {self.service_url}")

    def search_similar_incidents(self, query: str, **kwargs) -> List[SimilarIncident]:
        try:
            payload = {
                "query": query,
                "service_name": kwargs.get("service_name"),
                "alert_type": kwargs.get("alert_type"),
                "top_k": kwargs.get("top_k", RAG_TOP_K),
                "similarity_threshold": kwargs.get("similarity_threshold", RAG_SIMILARITY_THRESHOLD)
            }
            resp = requests.post(f"{self.service_url}/search", json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            results = []
            for item in data.get("results", []):
                incident = Incident(**item["incident"])
                results.append(SimilarIncident(incident=incident, similarity_score=item["similarity_score"]))
            return results
        except Exception as e:
            logger.error(f"KB HTTP search failed: {e}")
            return []

    def add_incident(self, incident: Incident) -> int:
        try:
            resp = requests.post(f"{self.service_url}/incidents", json=incident.dict(), timeout=30)
            resp.raise_for_status()
            return resp.json().get("id")
        except Exception as e:
            logger.error(f"KB HTTP add failed: {e}")
            raise

    def record_diagnosis_feedback(self, feedback: DiagnosisFeedback) -> int:
        try:
            resp = requests.post(f"{self.service_url}/feedback", json=feedback.dict(), timeout=30)
            resp.raise_for_status()
            return resp.json().get("id")
        except Exception as e:
            logger.error(f"KB HTTP feedback record failed: {e}")
            raise

    def get_alert_type_confidence(self, service_name: str, alert_type: str) -> Optional[AlertTypeStats]:
        try:
            params = {"service_name": service_name, "alert_type": alert_type}
            resp = requests.get(f"{self.service_url}/stats", params=params, timeout=10)
            if resp.status_code == 404: return None
            resp.raise_for_status()
            return AlertTypeStats(**resp.json())
        except Exception as e:
            logger.error(f"KB HTTP stats failed: {e}")
            return None

    def update_incident_reference(self, incident_id: str, successful: bool) -> None:
        try:
            payload = {"incident_id": incident_id, "successful": successful}
            requests.patch(f"{self.service_url}/incidents/reference", json=payload, timeout=10).raise_for_status()
        except Exception as e:
            logger.error(f"KB HTTP update reference failed: {e}")


class PostgreSQLKnowledgeBaseClient(KnowledgeBaseClient):
    """Direct PostgreSQL knowledge base client (legacy/fallback)."""
    # This would contain the full implementation from Chapter 4 if needed, 
    # but for Chapter 5 microservices, the Agent Core should primarily use HTTP.
    # To keep it simple, I'll just keep the structure if we want to run in monolith mode.
    def __init__(self, connection_string: str):
        from .postgresql_impl import PostgreSQLKnowledgeBaseImpl
        self.impl = PostgreSQLKnowledgeBaseImpl(connection_string)
    
    def search_similar_incidents(self, query: str, **kwargs) -> List[SimilarIncident]:
        return self.impl.search_similar_incidents(query, **kwargs)
    
    def add_incident(self, incident: Incident) -> int:
        return self.impl.add_incident(incident)
        
    def record_diagnosis_feedback(self, feedback: DiagnosisFeedback) -> int:
        return self.impl.record_diagnosis_feedback(feedback)
        
    def get_alert_type_confidence(self, service_name: str, alert_type: str) -> Optional[AlertTypeStats]:
        return self.impl.get_alert_type_confidence(service_name, alert_type)
        
    def update_incident_reference(self, incident_id: str, successful: bool) -> None:
        self.impl.update_incident_reference(incident_id, successful)

def get_kb_client() -> KnowledgeBaseClient:
    if DEPLOYMENT_MODE == "microservices":
        return HTTPKnowledgeBaseClient(KNOWLEDGE_BASE_URL)
    else:
        return PostgreSQLKnowledgeBaseClient(POSTGRES_URI)
