import logging
from typing import Optional
from .models import Incident, SimilarIncident, DiagnosisFeedback, AlertTypeStats
from .postgresql_impl import PostgreSQLKnowledgeBaseImpl

logger = logging.getLogger(__name__)

class PostgreSQLKnowledgeBaseClient:
    """Direct PostgreSQL knowledge base client for use INSIDE the microservice."""
    def __init__(self, connection_string: str):
        self.impl = PostgreSQLKnowledgeBaseImpl(connection_string)
    
    def _get_connection(self):
        return self.impl._get_connection()

    def search_similar_incidents(self, query: str, **kwargs) -> list[SimilarIncident]:
        return self.impl.search_similar_incidents(query, **kwargs)
    
    def add_incident(self, incident: Incident) -> int:
        return self.impl.add_incident(incident)
        
    def record_diagnosis_feedback(self, feedback: DiagnosisFeedback) -> int:
        return self.impl.record_diagnosis_feedback(feedback)
        
    def get_alert_type_confidence(self, service_name: str, alert_type: str) -> Optional[AlertTypeStats]:
        return self.impl.get_alert_type_confidence(service_name, alert_type)
        
    def update_incident_reference(self, incident_id: str, successful: bool) -> None:
        self.impl.update_incident_reference(incident_id, successful)
