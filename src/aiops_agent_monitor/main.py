"""FastAPI entrypoint for the AIOps diagnostic agent service with PostgreSQL checkpointing."""

from __future__ import annotations

import logging
import os
import time
import uuid
from typing import Any, Dict, Optional

from fastapi import Body, FastAPI, HTTPException, Request, Response
from langchain_core.messages import HumanMessage
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.postgres import PostgresSaver
from prometheus_client import Counter, Gauge, Histogram, generate_latest
from psycopg_pool import ConnectionPool
from psycopg.rows import dict_row

from agents import build_diagnostic_agent
from state import AgentState
from tools.mlops_tools import (
    GrafanaDashboardLink, LokiLogSearch, PrometheusQuery,
    prom_breaker, loki_breaker, kb_breaker, system_breaker
)

def configure_logging() -> logging.Logger:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    return logging.getLogger(__name__)


logger = configure_logging()

# Prometheus metrics -------------------------------------------------------
LLM_MODEL_INFO = Gauge(
    "aiops_monitor_agent_llm_model_info",
    "Information about the LLM model used by the agent",
    ["model_name"],
)

API_REQUEST_COUNT = Counter(
    "aiops_monitor_agent_api_requests_total",
    "Total number of requests to the AIOps Monitor Agent API",
)

API_REQUEST_LATENCY_SECONDS = Histogram(
    "aiops_monitor_agent_api_request_latency_seconds",
    "Latency of AIOps Monitor Agent API requests",
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
)

AGENT_RUN_COUNT = Counter(
    "aiops_monitor_agent_runs_total",
    "Total number of agent diagnostic runs triggered",
)

AGENT_ERROR_COUNT = Counter(
    "aiops_monitor_agent_errors_total",
    "Total number of agent execution errors",
    ["endpoint", "error_type"],
)

AGENT_STATUS_GAUGE = Gauge(
    "aiops_monitor_agent_status",
    "Current operational status of the AIOps Monitor Agent (1=online, 0=offline)",
)

AGENT_DIAGNOSIS_COUNT = Counter(
    "aiops_monitor_agent_diagnosis_total",
    "Count of diagnosis attempts",
    ["outcome"],
)

AGENT_STATUS_GAUGE.set(1)

def init_llm() -> BaseChatModel:
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY (or GROQ_API_KEY) environment variable not set.")

    model_name = os.getenv("GROQ_MODEL_NAME", "gpt-4o-mini")
    base_url = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
    try:
        llm = ChatOpenAI(model=model_name, temperature=0, api_key=api_key, base_url=base_url)
    except Exception as exc:  # pragma: no cover - startup failure
        logger.exception("Error initialising LLM")
        raise RuntimeError("Unable to initialise LLM client") from exc

    LLM_MODEL_INFO.labels(model_name=model_name).set(1)
    logger.info("LLM %s initialised successfully via %s.", model_name, base_url)
    return llm


def init_tools() -> list:
    # Chapter 3 tools + Chapter 4 RAG tool
    from tools.mlops_tools import RAGKnowledgeSearch, SystemMetrics
    tools = [PrometheusQuery, LokiLogSearch, GrafanaDashboardLink, SystemMetrics]
    
    # Dynamically enable RAG tool based on environment variable
    enable_rag = os.getenv("ENABLE_RAG_TOOL", "true").lower() == "true"
    if enable_rag:
        tools.append(RAGKnowledgeSearch)
    
    tool_names = [getattr(tool, "name", getattr(tool, "__name__", repr(tool))) for tool in tools]
    logger.info("Registered diagnostic tools: %s", ", ".join(tool_names))
    return tools

def init_checkpointer() -> PostgresSaver:
    """Initialize PostgreSQL checkpointer with connection pool."""
    postgres_host = os.getenv("POSTGRES_HOST", "postgres")
    postgres_port = os.getenv("POSTGRES_PORT", "5432")
    postgres_db = os.getenv("POSTGRES_DB", "agent_checkpoints")
    postgres_user = os.getenv("POSTGRES_USER", "agent_user")
    postgres_password = os.getenv("POSTGRES_PASSWORD", "agent_password")
    postgres_db_uri = (
        f"postgresql://{postgres_user}:{postgres_password}@"
        f"{postgres_host}:{postgres_port}/{postgres_db}?sslmode=disable"
    )

    try:
        # Create connection pool with proper configuration
        pool = ConnectionPool(
            conninfo=postgres_db_uri,
            max_size=20,
            kwargs={
                "autocommit": True,
                "prepare_threshold": 0,
                "row_factory": dict_row,
            },
        )
        
        # Create checkpointer with the pool
        checkpointer = PostgresSaver(conn=pool)
        checkpointer.setup()
        
        logger.info("PostgreSQL connection pool initialized and tables setup completed.")
        return checkpointer
    except Exception as exc:
        logger.exception("Error initializing PostgreSQL checkpointer")
        raise RuntimeError("Unable to initialize PostgreSQL checkpointer") from exc

LLM_CLIENT = init_llm()
DIAGNOSTIC_TOOLS = init_tools()
CHECKPOINTER = init_checkpointer()
DIAGNOSTIC_AGENT = build_diagnostic_agent(LLM_CLIENT, DIAGNOSTIC_TOOLS, checkpointer=CHECKPOINTER)

def classify_outcome(final_message: str, final_result: str | None) -> str:
    text = f"{final_message} {final_result or ''}".lower()
    if any(keyword in text for keyword in ("critical", "escalated")):
        return "escalated"
    if any(keyword in text for keyword in ("solution", "resolve", "mitigat")):
        return "solution_proposed"
    return "info"


def build_initial_state(alert_info: str, thread_id: str, diagnosis_id: str) -> AgentState:
    return AgentState(
        messages=[HumanMessage(content=f"Diagnose this alert: {alert_info}")],
        alert_info=alert_info,
        alert_severity="unknown",
        prometheus_data="",
        loki_logs="",
        grafana_link="",
        # Chapter 4 - RAG and learning fields
        rag_similar_incidents=None,
        historical_context_used=False,
        diagnosis_id=diagnosis_id,
        confidence_score=None,
        recommended_action="unknown",
        final_result=None,
        investigation_query="",
        investigation_step=0,
        max_investigation_steps=0,
        logs_found=False,
        proposed_action=None,
        human_feedback=None,
        system_metrics={},
        report_content="",
        thread_id=thread_id,
    )


def render_alert_info(alert_payload: Dict[str, Any]) -> tuple[str, str]:
    alert = (alert_payload.get("alerts") or [{}])[0]
    labels = alert.get("labels", {})
    annotations = alert.get("annotations", {})
    name = labels.get("alertname", "Unknown Alert")
    service = labels.get("service", "Unknown Service")
    summary = annotations.get("summary", "No summary provided.")
    fingerprint = alert.get("fingerprint", str(uuid.uuid4()))
    alert_info = f"Alert '{name}' for service '{service}': {summary}"
    return alert_info, fingerprint


app = FastAPI(
    title="AIOps Diagnostic Agent Service",
    description="API for the MLOps Guard Agent, capable of diagnosing issues using Prometheus and Loki.",
)


# --- Middleware for request metrics ---
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    API_REQUEST_COUNT.inc()
    start_time = time.time()
    try:
        response = await call_next(request)
        return response
    except Exception as exc:
        AGENT_ERROR_COUNT.labels(endpoint=request.url.path, error_type=type(exc).__name__).inc()
        logger.exception("Unhandled API error")
        raise
    finally:
        process_time = time.time() - start_time
        API_REQUEST_LATENCY_SECONDS.observe(process_time)
        logger.info("API request to %s took %.4f seconds.", request.url.path, process_time)


# --- Routes ---
@app.get("/")
async def read_root():
    logger.info("Received request to root endpoint.")
    return {"message": "AIOps Diagnostic Agent Service is running and ready to diagnose alerts!"}

@app.get("/health")
def health():
    return {"status": "ok", "service": "aiops-agent-monitor"}

@app.get("/ready")
def ready():
    # Basic check: is the tool list initialized?
    if DIAGNOSTIC_TOOLS:
        return {"status": "ready"}
    else:
        raise HTTPException(status_code=503, detail="Agent tools not initialized")

@app.get("/circuit_breakers")
def get_circuit_breaker_states():
    """
    Expose circuit breaker states for gateway-level fail-fast decisions.
    Production pattern: Gateway checks this before forwarding requests.
    
    Uses get_effective_state() to properly handle HALF-OPEN transitions:
    - OPEN: Block requests (service is down)
    - HALF-OPEN: Allow requests (testing if service recovered)
    - CLOSED: Allow requests (service is healthy)
    """
    breakers = {
        "prometheus": {
            "state": prom_breaker.state,
            "effective_state": prom_breaker.get_effective_state(),
            "failures": prom_breaker.failures,
            "is_blocking": prom_breaker.is_blocking()
        },
        "loki": {
            "state": loki_breaker.state,
            "effective_state": loki_breaker.get_effective_state(),
            "failures": loki_breaker.failures,
            "is_blocking": loki_breaker.is_blocking()
        },
        "knowledge_base": {
            "state": kb_breaker.state,
            "effective_state": kb_breaker.get_effective_state(),
            "failures": kb_breaker.failures,
            "is_blocking": kb_breaker.is_blocking()
        },
        "system": {
            "state": system_breaker.state,
            "effective_state": system_breaker.get_effective_state(),
            "failures": system_breaker.failures,
            "is_blocking": system_breaker.is_blocking()
        },
    }
    
    # Check if any critical circuit is actively blocking (OPEN, not HALF-OPEN)
    critical_open = prom_breaker.is_blocking()
    
    return {
        "breakers": breakers,
        "critical_service_unavailable": critical_open,
        "degraded_mode": loki_breaker.is_blocking() or kb_breaker.is_blocking()
    }

@app.post("/diagnose_alert")
async def diagnose_alert(alert_payload: Dict[str, Any] = Body(...)):
    AGENT_RUN_COUNT.inc()
    alert_info, fingerprint = render_alert_info(alert_payload)
    logger.info("Received alert for diagnosis: %s", alert_info)

    thread_id = f"alert_diagnosis_{fingerprint}"
    diagnosis_id = f"diag-{uuid.uuid4().hex[:12]}"  # Unique diagnosis ID
    config = {"configurable": {"thread_id": thread_id}}
    start_time = time.time()

    try:
        final_state = DIAGNOSTIC_AGENT.invoke(
            build_initial_state(alert_info, thread_id, diagnosis_id), config=config
        )
        messages = final_state.get("messages", [])
        final_message = (
            messages[-1].content
            if messages
            else final_state.get("final_result", "No final message from agent.")
        )
        outcome = classify_outcome(final_message, final_state.get("final_result"))
        AGENT_DIAGNOSIS_COUNT.labels(outcome=outcome).inc()
        logger.info("Agent diagnostic run completed. Outcome: %s", outcome)
        return {
            "status": "success",
            "agent_diagnosis": final_message,
            "thread_id": thread_id,
            "diagnosis_id": diagnosis_id,  # For feedback tracking
            "confidence_score": final_state.get("confidence_score"),
            "recommended_action": final_state.get("recommended_action"),
            "current_agent_state": final_state,
        }

    except Exception as exc:
        AGENT_ERROR_COUNT.labels(endpoint="/diagnose_alert", error_type=type(exc).__name__).inc()
        AGENT_DIAGNOSIS_COUNT.labels(outcome="failed").inc()
        logger.exception("AIOps agent diagnosis failure")
        raise HTTPException(status_code=500, detail=f"Agent diagnostic failed: {exc}") from exc
    finally:
        duration = time.time() - start_time
        logger.info("Agent diagnostic run for alert took %.4f seconds.", duration)

@app.post("/resume_diagnosis/{thread_id}")
async def resume_diagnosis(thread_id: str):
    """
    Resume a diagnosis session from a checkpoint.
    
    Passing None as input tells LangGraph: "Don't start new work, just load the state 
    from the checkpoint and continue if there's work left, or return the state if finished."
    """
    logger.info(f"Resuming diagnosis for thread_id: {thread_id}")
    
    config = {"configurable": {"thread_id": thread_id}}
    start_time = time.time()
    
    try:
        # Invoke with None to resume from checkpoint
        final_state = DIAGNOSTIC_AGENT.invoke(None, config=config)
        messages = final_state.get("messages", [])
        final_message = (
            messages[-1].content
            if messages
            else final_state.get("final_result", "No final message from agent.")
        )
        
        logger.info(f"Resumed diagnosis completed for thread_id: {thread_id}")
        return {
            "status": "success",
            "thread_id": thread_id,
            "agent_diagnosis": final_message,
            "current_agent_state": final_state,
        }
    
    except Exception as exc:
        logger.exception(f"Error resuming diagnosis for thread_id {thread_id}: {exc}")
        raise HTTPException(status_code=500, detail=f"Failed to resume diagnosis: {exc}") from exc
    finally:
        duration = time.time() - start_time
        logger.info(f"Resume diagnosis for thread_id {thread_id} took {duration:.4f} seconds.")

@app.get("/metrics")
async def prometheus_metrics():
    return Response(content=generate_latest(), media_type="text/plain")


# --- Chapter 4 - Part 3: Feedback Loop Endpoint ---
@app.post("/feedback")
async def record_feedback(feedback_data: Dict[str, Any] = Body(...)):
    """
    Record feedback on a diagnosis to enable continuous learning.

    Expected payload:
    {
        "diagnosis_id": "diag-abc123",
        "outcome": "success" | "partial_success" | "failure" | "escalated",
        "human_correction": "Optional explanation",
        "corrected_root_cause": "Optional corrected diagnosis",
        "corrected_solution": "Optional corrected solution",
        "add_to_knowledge_base": true  # If true, adds successful resolution to KB
    }
    """
    logger.info(f"Received feedback for diagnosis: {feedback_data.get('diagnosis_id')}")

    try:
        from knowledge_base import get_kb_client, DiagnosisFeedback, Incident
        from datetime import datetime

        diagnosis_id = feedback_data.get("diagnosis_id")
        if not diagnosis_id:
            raise ValueError("diagnosis_id is required")

        outcome = feedback_data.get("outcome")
        if outcome not in ["success", "partial_success", "failure", "escalated"]:
            raise ValueError(
                "outcome must be one of: success, partial_success, failure, escalated"
            )

        # Create feedback record
        feedback = DiagnosisFeedback(
            diagnosis_id=diagnosis_id,
            thread_id=feedback_data.get("thread_id", ""),
            alert_info=feedback_data.get("alert_info", ""),
            service_name=feedback_data.get("service_name"),
            alert_type=feedback_data.get("alert_type"),
            proposed_root_cause=feedback_data.get("proposed_root_cause"),
            proposed_solution=feedback_data.get("proposed_solution"),
            confidence_score=feedback_data.get("confidence_score"),
            outcome=outcome,
            human_correction=feedback_data.get("human_correction"),
            corrected_root_cause=feedback_data.get("corrected_root_cause"),
            corrected_solution=feedback_data.get("corrected_solution"),
            diagnosed_at=datetime.fromisoformat(feedback_data.get("diagnosed_at", datetime.now().isoformat())),
            feedback_received_at=datetime.now(),
        )

        # Record in database (triggers automatic stats update via DB trigger)
        kb_client = get_kb_client()
        feedback_id = kb_client.record_diagnosis_feedback(feedback)
        logger.info(f"Recorded feedback with id={feedback_id}")

        # If successful and user wants to add to KB, create incident entry
        if feedback_data.get("add_to_knowledge_base", False) and outcome in [
            "success",
            "partial_success",
        ]:
            incident = Incident(
                incident_id=diagnosis_id,
                service_name=feedback_data.get("service_name", "unknown"),
                alert_type=feedback_data.get("alert_type", "unknown"),
                severity=feedback_data.get("severity", "medium"),
                summary=feedback_data.get("alert_info", ""),
                root_cause=feedback_data.get("corrected_root_cause")
                or feedback_data.get("proposed_root_cause", ""),
                solution=feedback_data.get("corrected_solution")
                or feedback_data.get("proposed_solution", ""),
                occurred_at=datetime.fromisoformat(feedback_data.get("diagnosed_at", datetime.now().isoformat())),
                resolved_at=datetime.now(),
                resolution_time_seconds=feedback_data.get("resolution_time_seconds", 0),
            )
            incident_id = kb_client.add_incident(incident)
            logger.info(f"Added incident to knowledge base: {incident_id}")

            return {
                "status": "success",
                "message": "Feedback recorded and added to knowledge base",
                "feedback_id": feedback_id,
                "incident_id": incident_id,
            }
        else:
            return {
                "status": "success",
                "message": "Feedback recorded",
                "feedback_id": feedback_id,
            }

    except ValueError as e:
        logger.error(f"Validation error in feedback: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.exception(f"Error recording feedback: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to record feedback: {e}")


__all__ = ["app"]
