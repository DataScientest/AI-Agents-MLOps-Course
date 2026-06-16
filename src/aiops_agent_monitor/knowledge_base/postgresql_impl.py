import logging
from typing import List, Optional, Any
from datetime import datetime
import psycopg
from pgvector.psycopg import register_vector
from langchain_openai import OpenAIEmbeddings
from langchain_core.embeddings import Embeddings
import requests

from config import (
    EMBEDDING_PROVIDER,
    EMBEDDING_MODEL,
    OPENAI_API_KEY,
    OPENAI_API_BASE,
    HUGGINGFACE_TEI_URL,
    RAG_TOP_K,
    RAG_SIMILARITY_THRESHOLD,
)
from .models import Incident, SimilarIncident, DiagnosisFeedback, AlertTypeStats

logger = logging.getLogger(__name__)

class TEIEmbeddings(Embeddings):
    def __init__(self, endpoint_url: str):
        self.endpoint_url = endpoint_url.rstrip('/')
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        resp = requests.post(self.endpoint_url, json={"inputs": texts})
        resp.raise_for_status()
        return resp.json()
    def embed_query(self, text: str) -> List[float]:
        return self.embed_documents([text])[0]

class PostgreSQLKnowledgeBaseImpl:
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.embeddings = self._init_embeddings()

    def _init_embeddings(self):
        if EMBEDDING_PROVIDER == "openai":
            return OpenAIEmbeddings(api_key=OPENAI_API_KEY, model=EMBEDDING_MODEL, base_url=OPENAI_API_BASE)
        elif EMBEDDING_PROVIDER == "huggingface-tei":
            return TEIEmbeddings(endpoint_url=HUGGINGFACE_TEI_URL)
        raise ValueError(f"Unsupported provider: {EMBEDDING_PROVIDER}")

    def _get_connection(self):
        conn = psycopg.connect(self.connection_string)
        register_vector(conn)
        return conn

    def search_similar_incidents(self, query: str, **kwargs) -> List[SimilarIncident]:
        top_k = kwargs.get("top_k", RAG_TOP_K)
        threshold = kwargs.get("similarity_threshold", RAG_SIMILARITY_THRESHOLD)
        emb = self.embeddings.embed_query(query)
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    sql = """
                        SELECT id, incident_id, service_name, alert_type, severity, summary, root_cause, solution,
                               occurred_at, resolved_at, resolution_time_seconds, times_referenced, success_count, 
                               failure_count, confidence_score, created_at, updated_at,
                               1 - (embedding <=> %s::vector) as similarity
                        FROM incident_knowledge
                        WHERE (1 - (embedding <=> %s::vector)) >= %s
                        ORDER BY embedding <=> %s::vector LIMIT %s
                    """
                    cur.execute(sql, (emb, emb, threshold, emb, top_k))
                    rows = cur.fetchall()
                    return [SimilarIncident(incident=Incident(
                        id=r[0], incident_id=r[1], service_name=r[2], alert_type=r[3], 
                        severity=r[4], summary=r[5], root_cause=r[6], solution=r[7],
                        occurred_at=r[8], resolved_at=r[9], resolution_time_seconds=r[10],
                        times_referenced=r[11], success_count=r[12], failure_count=r[13],
                        confidence_score=r[14], created_at=r[15], updated_at=r[16]
                    ), similarity_score=float(r[17])) for r in rows]
        except Exception as e:
            logger.error(f"PostgreSQL search failed: {e}")
            return []

    def add_incident(self, incident: Incident) -> int:
        text = f"{incident.summary} {incident.root_cause} {incident.solution}"
        emb = self.embeddings.embed_query(text)
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                sql = """
                    INSERT INTO incident_knowledge (incident_id, service_name, alert_type, severity, summary, root_cause, solution, embedding)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (incident_id) DO UPDATE SET summary=EXCLUDED.summary, root_cause=EXCLUDED.root_cause, solution=EXCLUDED.solution, embedding=EXCLUDED.embedding, updated_at=NOW()
                    RETURNING id
                """
                cur.execute(sql, (incident.incident_id, incident.service_name, incident.alert_type, incident.severity, incident.summary, incident.root_cause, incident.solution, emb))
                res = cur.fetchone()[0]
                conn.commit()
                return res

    def record_diagnosis_feedback(self, feedback: DiagnosisFeedback) -> int:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                sql = """
                    INSERT INTO diagnosis_feedback (diagnosis_id, thread_id, alert_info, service_name, alert_type, proposed_root_cause, proposed_solution, confidence_score, outcome)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """
                cur.execute(sql, (feedback.diagnosis_id, feedback.thread_id, feedback.alert_info, feedback.service_name, feedback.alert_type, feedback.proposed_root_cause, feedback.proposed_solution, feedback.confidence_score, feedback.outcome))
                res = cur.fetchone()[0]
                conn.commit()
                return res

    def get_alert_type_confidence(self, service_name: str, alert_type: str) -> Optional[AlertTypeStats]:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                sql = "SELECT id, service_name, alert_type, total_diagnoses, successful_diagnoses, failed_diagnoses, escalated_diagnoses, avg_resolution_time_seconds, confidence_score, last_updated FROM alert_type_stats WHERE service_name = %s AND alert_type = %s"
                cur.execute(sql, (service_name, alert_type))
                r = cur.fetchone()
                if not r: return None
                return AlertTypeStats(id=r[0], service_name=r[1], alert_type=r[2], total_diagnoses=r[3], successful_diagnoses=r[4], failed_diagnoses=r[5], escalated_diagnoses=r[6], avg_resolution_time_seconds=r[7], confidence_score=r[8], last_updated=r[9])

    def update_incident_reference(self, incident_id: str, successful: bool) -> None:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                if successful:
                    sql = "UPDATE incident_knowledge SET times_referenced = times_referenced + 1, success_count = success_count + 1 WHERE incident_id = %s"
                else:
                    sql = "UPDATE incident_knowledge SET times_referenced = times_referenced + 1, failure_count = failure_count + 1 WHERE incident_id = %s"
                cur.execute(sql, (incident_id,))
                conn.commit()
