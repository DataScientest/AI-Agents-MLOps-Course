import logging
import os
import sys
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Body, status
from pydantic import BaseModel

# Add src to path to import knowledge_base
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from knowledge_base.client import PostgreSQLKnowledgeBaseClient
from knowledge_base.models import Incident, SimilarIncident, DiagnosisFeedback, AlertTypeStats
from config import POSTGRES_URI

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="Knowledge Base Service", description="Microservice for handling RAG and incident history.")

# Initialize KB Client (Direct PostgreSQL access internal to this service)
try:
    kb_client = PostgreSQLKnowledgeBaseClient(POSTGRES_URI)
    logger.info("Knowledge Base Client (PostgreSQL) initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize Knowledge Base Client: {e}")
    sys.exit(1)

# --- Models for API Request/Response ---

class SearchRequest(BaseModel):
    query: str
    service_name: Optional[str] = None
    alert_type: Optional[str] = None
    top_k: int = 3
    similarity_threshold: float = 0.7

# --- Endpoints ---

@app.get("/health")
def health():
    return {"status": "ok", "service": "knowledge-base-service"}

@app.get("/ready")
def ready():
    # Simple check to see if we can connect to DB
    try:
        with kb_client._get_connection() as conn:
            pass
        return {"status": "ready"}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=503, detail="Database connection failed")

@app.post("/search", response_model=Dict[str, Any])
def search_incidents(request: SearchRequest):
    logger.info(f"Searching for incidents: {request.query}")
    try:
        results = kb_client.search_similar_incidents(
            query=request.query,
            service_name=request.name if hasattr(request, 'name') else request.service_name,
            alert_type=request.alert_type,
            top_k=request.top_k,
            similarity_threshold=request.similarity_threshold
        )
        return {"results": [r.dict() for r in results]}
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/incidents", status_code=status.HTTP_201_CREATED)
def add_incident(incident: Incident):
    logger.info(f"Adding incident: {incident.incident_id}")
    try:
        kb_id = kb_client.add_incident(incident)
        return {"id": kb_id}
    except Exception as e:
        logger.error(f"Failed to add incident: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/feedback")
def record_feedback(feedback: DiagnosisFeedback):
    logger.info(f"Recording feedback for: {feedback.diagnosis_id}")
    try:
        feedback_id = kb_client.record_diagnosis_feedback(feedback)
        return {"id": feedback_id}
    except Exception as e:
        logger.error(f"Failed to record feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats", response_model=Optional[AlertTypeStats])
def get_stats(service_name: str, alert_type: str):
    logger.info(f"Fetching stats for {service_name}/{alert_type}")
    try:
        stats = kb_client.get_alert_type_confidence(service_name, alert_type)
        if not stats:
            raise HTTPException(status_code=404, detail="Stats not found")
        return stats
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/incidents/reference")
def update_reference(payload: Dict[str, Any] = Body(...)):
    incident_id = payload.get("incident_id")
    successful = payload.get("successful", True)
    if not incident_id:
        raise HTTPException(status_code=400, detail="incident_id required")
    
    try:
        kb_client.update_incident_reference(incident_id, successful)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Failed to update reference: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8006)
