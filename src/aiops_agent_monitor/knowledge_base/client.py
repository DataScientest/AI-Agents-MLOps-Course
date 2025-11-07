"""Knowledge Base client with abstraction for monolith vs microservices deployment.

This module provides a unified interface for knowledge base operations that works
in both Chapter 4 (monolithic, direct PostgreSQL) and Chapter 5 (microservices, HTTP).
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime

import psycopg
import requests
from pgvector.psycopg import register_vector
from langchain_openai import OpenAIEmbeddings
from langchain_core.embeddings import Embeddings

from config import (
    POSTGRES_URI,
    DEPLOYMENT_MODE,
    KNOWLEDGE_BASE_URL,
    EMBEDDING_PROVIDER,
    EMBEDDING_MODEL,
    OPENAI_API_KEY,
    HUGGINGFACE_TEI_URL,
    RAG_TOP_K,
    RAG_SIMILARITY_THRESHOLD,
)
from .models import Incident, SimilarIncident, DiagnosisFeedback, AlertTypeStats

logger = logging.getLogger(__name__)


class TEIEmbeddings(Embeddings):
    """Custom embeddings class for Text Embeddings Inference (TEI) endpoint."""
    
    def __init__(self, endpoint_url: str):
        """Initialize with TEI endpoint URL."""
        self.endpoint_url = endpoint_url.rstrip('/')
        
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents."""
        response = requests.post(
            self.endpoint_url,
            json={"inputs": texts},
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        return response.json()
    
    def embed_query(self, text: str) -> List[float]:
        """Embed a single query."""
        return self.embed_documents([text])[0]


class KnowledgeBaseClient(ABC):
    """Abstract base class for knowledge base access."""

    @abstractmethod
    def search_similar_incidents(
        self,
        query: str,
        service_name: Optional[str] = None,
        alert_type: Optional[str] = None,
        top_k: int = RAG_TOP_K,
        similarity_threshold: float = RAG_SIMILARITY_THRESHOLD,
    ) -> List[SimilarIncident]:
        """Search for similar incidents using semantic search."""
        pass

    @abstractmethod
    def add_incident(self, incident: Incident) -> int:
        """Add a new incident to the knowledge base."""
        pass

    @abstractmethod
    def record_diagnosis_feedback(self, feedback: DiagnosisFeedback) -> int:
        """Record feedback on a diagnosis."""
        pass

    @abstractmethod
    def get_alert_type_confidence(
        self, service_name: str, alert_type: str
    ) -> Optional[AlertTypeStats]:
        """Get confidence score for a specific alert type."""
        pass

    @abstractmethod
    def update_incident_reference(self, incident_id: str, successful: bool) -> None:
        """Update times_referenced and success/failure counts for an incident."""
        pass


class PostgreSQLKnowledgeBaseClient(KnowledgeBaseClient):
    """Direct PostgreSQL knowledge base client (for Chapter 4 monolith)."""

    def __init__(self, connection_string: str):
        """Initialize with PostgreSQL connection string."""
        self.connection_string = connection_string
        self.embeddings = self._init_embeddings()
        logger.info(
            f"Initialized PostgreSQL KB client with {EMBEDDING_PROVIDER} embeddings"
        )

    def _init_embeddings(self):
        """Initialize embedding model based on provider."""
        if EMBEDDING_PROVIDER == "openai":
            if not OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY required for OpenAI embeddings")
            logger.info(f"Using OpenAI embeddings: {EMBEDDING_MODEL}")
            return OpenAIEmbeddings(
                api_key=OPENAI_API_KEY,
                model=EMBEDDING_MODEL,
            )
        elif EMBEDDING_PROVIDER == "huggingface-tei":
            logger.info(f"Using HuggingFace TEI embeddings at {HUGGINGFACE_TEI_URL}")
            return TEIEmbeddings(endpoint_url=HUGGINGFACE_TEI_URL)
        else:
            raise ValueError(
                f"Unsupported embedding provider: {EMBEDDING_PROVIDER}. "
                f"Supported: 'openai', 'huggingface-tei'"
            )

    def _get_connection(self):
        """Get a database connection with pgvector support."""
        conn = psycopg.connect(self.connection_string)
        register_vector(conn)
        return conn

    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text."""
        try:
            return self.embeddings.embed_query(text)
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise

    def search_similar_incidents(
        self,
        query: str,
        service_name: Optional[str] = None,
        alert_type: Optional[str] = None,
        top_k: int = RAG_TOP_K,
        similarity_threshold: float = RAG_SIMILARITY_THRESHOLD,
    ) -> List[SimilarIncident]:
        """Search for similar incidents using pgvector similarity search."""
        logger.info(
            f"Searching similar incidents: query='{query[:50]}...', service={service_name}, top_k={top_k}"
        )

        try:
            # Generate query embedding
            query_embedding = self._generate_embedding(query)

            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    # Build SQL query with optional filters
                    sql = """
                        SELECT
                            id, incident_id, service_name, alert_type, severity,
                            summary, root_cause, solution,
                            occurred_at, resolved_at, resolution_time_seconds,
                            times_referenced, success_count, failure_count, confidence_score,
                            created_at, updated_at,
                            1 - (embedding <=> %s::vector) as similarity
                        FROM incident_knowledge
                        WHERE 1=1
                    """
                    params = [query_embedding]

                    if service_name:
                        sql += " AND service_name = %s"
                        params.append(service_name)

                    if alert_type:
                        sql += " AND alert_type = %s"
                        params.append(alert_type)

                    sql += """
                        AND (1 - (embedding <=> %s::vector)) >= %s
                        ORDER BY embedding <=> %s::vector
                        LIMIT %s
                    """
                    params.extend([query_embedding, similarity_threshold, query_embedding, top_k])

                    cur.execute(sql, params)
                    rows = cur.fetchall()

                    results = []
                    for row in rows:
                        incident = Incident(
                            id=row[0],
                            incident_id=row[1],
                            service_name=row[2],
                            alert_type=row[3],
                            severity=row[4],
                            summary=row[5],
                            root_cause=row[6],
                            solution=row[7],
                            occurred_at=row[8],
                            resolved_at=row[9],
                            resolution_time_seconds=row[10],
                            times_referenced=row[11],
                            success_count=row[12],
                            failure_count=row[13],
                            confidence_score=row[14],
                            created_at=row[15],
                            updated_at=row[16],
                        )
                        results.append(
                            SimilarIncident(
                                incident=incident, similarity_score=float(row[17])
                            )
                        )

                    logger.info(f"Found {len(results)} similar incidents")
                    return results

        except Exception as e:
            logger.exception(f"Error searching incidents: {e}")
            return []

    def add_incident(self, incident: Incident) -> int:
        """Add a new incident to knowledge base with embedding."""
        logger.info(f"Adding incident: {incident.incident_id}")

        try:
            # Generate embedding from summary + root_cause + solution
            text_to_embed = f"{incident.summary} {incident.root_cause} {incident.solution}"
            embedding = self._generate_embedding(text_to_embed)

            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    sql = """
                        INSERT INTO incident_knowledge (
                            incident_id, service_name, alert_type, severity,
                            summary, root_cause, solution, embedding,
                            occurred_at, resolved_at, resolution_time_seconds,
                            times_referenced, success_count, failure_count, confidence_score
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                        ON CONFLICT (incident_id) DO UPDATE SET
                            summary = EXCLUDED.summary,
                            root_cause = EXCLUDED.root_cause,
                            solution = EXCLUDED.solution,
                            embedding = EXCLUDED.embedding,
                            updated_at = NOW()
                        RETURNING id
                    """
                    cur.execute(
                        sql,
                        (
                            incident.incident_id,
                            incident.service_name,
                            incident.alert_type,
                            incident.severity,
                            incident.summary,
                            incident.root_cause,
                            incident.solution,
                            embedding,
                            incident.occurred_at,
                            incident.resolved_at,
                            incident.resolution_time_seconds,
                            incident.times_referenced,
                            incident.success_count,
                            incident.failure_count,
                            incident.confidence_score,
                        ),
                    )
                    incident_id = cur.fetchone()[0]
                    conn.commit()
                    logger.info(f"Added incident with id={incident_id}")
                    return incident_id

        except Exception as e:
            logger.exception(f"Error adding incident: {e}")
            raise

    def record_diagnosis_feedback(self, feedback: DiagnosisFeedback) -> int:
        """Record diagnosis feedback (triggers stats update automatically via DB trigger)."""
        logger.info(f"Recording feedback for diagnosis: {feedback.diagnosis_id}")

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    sql = """
                        INSERT INTO diagnosis_feedback (
                            diagnosis_id, thread_id, alert_info, service_name, alert_type,
                            proposed_root_cause, proposed_solution, confidence_score,
                            outcome, human_correction, corrected_root_cause, corrected_solution,
                            diagnosed_at, feedback_received_at
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                        ON CONFLICT (diagnosis_id) DO UPDATE SET
                            outcome = EXCLUDED.outcome,
                            human_correction = EXCLUDED.human_correction,
                            corrected_root_cause = EXCLUDED.corrected_root_cause,
                            corrected_solution = EXCLUDED.corrected_solution,
                            feedback_received_at = EXCLUDED.feedback_received_at
                        RETURNING id
                    """
                    cur.execute(
                        sql,
                        (
                            feedback.diagnosis_id,
                            feedback.thread_id,
                            feedback.alert_info,
                            feedback.service_name,
                            feedback.alert_type,
                            feedback.proposed_root_cause,
                            feedback.proposed_solution,
                            feedback.confidence_score,
                            feedback.outcome,
                            feedback.human_correction,
                            feedback.corrected_root_cause,
                            feedback.corrected_solution,
                            feedback.diagnosed_at,
                            feedback.feedback_received_at or datetime.now(),
                        ),
                    )
                    feedback_id = cur.fetchone()[0]
                    conn.commit()
                    logger.info(f"Recorded feedback with id={feedback_id}")
                    return feedback_id

        except Exception as e:
            logger.exception(f"Error recording feedback: {e}")
            raise

    def get_alert_type_confidence(
        self, service_name: str, alert_type: str
    ) -> Optional[AlertTypeStats]:
        """Get confidence statistics for a specific alert type."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    sql = """
                        SELECT
                            id, service_name, alert_type,
                            total_diagnoses, successful_diagnoses, failed_diagnoses, escalated_diagnoses,
                            avg_resolution_time_seconds, confidence_score, last_updated
                        FROM alert_type_stats
                        WHERE service_name = %s AND alert_type = %s
                    """
                    cur.execute(sql, (service_name, alert_type))
                    row = cur.fetchone()

                    if row:
                        return AlertTypeStats(
                            id=row[0],
                            service_name=row[1],
                            alert_type=row[2],
                            total_diagnoses=row[3],
                            successful_diagnoses=row[4],
                            failed_diagnoses=row[5],
                            escalated_diagnoses=row[6],
                            avg_resolution_time_seconds=row[7],
                            confidence_score=row[8],
                            last_updated=row[9],
                        )
                    return None

        except Exception as e:
            logger.exception(f"Error getting alert type confidence: {e}")
            return None

    def update_incident_reference(self, incident_id: str, successful: bool) -> None:
        """Update times an incident was referenced and success/failure counts."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    if successful:
                        sql = """
                            UPDATE incident_knowledge
                            SET times_referenced = times_referenced + 1,
                                success_count = success_count + 1,
                                confidence_score = (success_count + 1.0) / (times_referenced + 1.0),
                                updated_at = NOW()
                            WHERE incident_id = %s
                        """
                    else:
                        sql = """
                            UPDATE incident_knowledge
                            SET times_referenced = times_referenced + 1,
                                failure_count = failure_count + 1,
                                confidence_score = success_count::FLOAT / (times_referenced + 1.0),
                                updated_at = NOW()
                            WHERE incident_id = %s
                        """
                    cur.execute(sql, (incident_id,))
                    conn.commit()
                    logger.info(
                        f"Updated incident reference: {incident_id}, successful={successful}"
                    )

        except Exception as e:
            logger.exception(f"Error updating incident reference: {e}")


class HTTPKnowledgeBaseClient(KnowledgeBaseClient):
    """HTTP-based knowledge base client (for Chapter 5 microservices).

    This client will make HTTP requests to a dedicated knowledge base service.
    For now, it's a placeholder that raises NotImplementedError.
    """

    def __init__(self, service_url: str):
        self.service_url = service_url
        logger.info(f"Initialized HTTP KB client for {service_url}")

    def search_similar_incidents(self, query: str, **kwargs) -> List[SimilarIncident]:
        raise NotImplementedError(
            "HTTP KB client will be implemented in Chapter 5 (microservices)"
        )

    def add_incident(self, incident: Incident) -> int:
        raise NotImplementedError(
            "HTTP KB client will be implemented in Chapter 5 (microservices)"
        )

    def record_diagnosis_feedback(self, feedback: DiagnosisFeedback) -> int:
        raise NotImplementedError(
            "HTTP KB client will be implemented in Chapter 5 (microservices)"
        )

    def get_alert_type_confidence(
        self, service_name: str, alert_type: str
    ) -> Optional[AlertTypeStats]:
        raise NotImplementedError(
            "HTTP KB client will be implemented in Chapter 5 (microservices)"
        )

    def update_incident_reference(self, incident_id: str, successful: bool) -> None:
        raise NotImplementedError(
            "HTTP KB client will be implemented in Chapter 5 (microservices)"
        )


def get_kb_client() -> KnowledgeBaseClient:
    """Factory function to get appropriate KB client based on deployment mode.

    Returns:
        PostgreSQLKnowledgeBaseClient for monolith mode (Chapter 4)
        HTTPKnowledgeBaseClient for microservices mode (Chapter 5)
    """
    if DEPLOYMENT_MODE == "microservices":
        logger.info("Using HTTP KB client for microservices deployment")
        return HTTPKnowledgeBaseClient(KNOWLEDGE_BASE_URL)
    else:
        logger.info("Using PostgreSQL KB client for monolithic deployment")
        return PostgreSQLKnowledgeBaseClient(POSTGRES_URI)
