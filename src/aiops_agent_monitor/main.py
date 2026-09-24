"""FastAPI entrypoint for the AIOps diagnostic agent service."""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict

from dotenv import load_dotenv
from fastapi import Body, FastAPI, HTTPException, Request, Response
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from prometheus_client import Counter, Gauge, Histogram, generate_latest

from agents import build_diagnostic_agent
from guardrails import degraded_diagnosis_message, invoke_diagnosis, tools_called
from llm_settings import resolve_llm_settings
from nodes.llm import LLMRateLimitError
from state import AgentState
from tools.mlops_tools import GrafanaDashboardLink, LokiLogSearch, PrometheusQuery

load_dotenv(override=True)


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
    # Groq through its OpenAI-compatible API: GROQ_API_KEY + GROQ_MODEL_NAME,
    # endpoint LLM_API_BASE (optional, default: https://api.groq.com/openai/v1).
    model_name, api_key, base_url = resolve_llm_settings()
    if not api_key:
        raise RuntimeError("GROQ_API_KEY environment variable not set for AIOps Agent Service.")

    try:
        llm = ChatOpenAI(model=model_name, temperature=0, api_key=api_key, base_url=base_url)
    except Exception as exc:  # pragma: no cover - startup failure
        logger.exception("Error initialising LLM for deployed monitor agent")
        raise RuntimeError("Unable to initialise LLM client") from exc

    LLM_MODEL_INFO.labels(model_name=model_name).set(1)
    logger.info("LLM %s initialised successfully via %s.", model_name, base_url)
    return llm


def init_tools() -> list:
    tools = [PrometheusQuery, LokiLogSearch, GrafanaDashboardLink]
    tool_names = [getattr(tool, "name", getattr(tool, "__name__", repr(tool))) for tool in tools]
    logger.info("Registered diagnostic tools: %s", ", ".join(tool_names))
    return tools


LLM_CLIENT = init_llm()
DIAGNOSTIC_TOOLS = init_tools()
DIAGNOSTIC_AGENT = build_diagnostic_agent(LLM_CLIENT, DIAGNOSTIC_TOOLS)


def classify_outcome(final_message: str, final_result: str | None) -> str:
    text = f"{final_message} {final_result or ''}".lower()
    if any(keyword in text for keyword in ("critical", "escalated")):
        return "escalated"
    if any(keyword in text for keyword in ("solution", "resolve", "mitigat")):
        return "solution_proposed"
    return "info"


def build_initial_state(alert_info: str) -> AgentState:
    return AgentState(
        messages=[HumanMessage(content=f"Diagnose this alert: {alert_info}")],
        alert_info=alert_info,
        alert_severity="unknown",
        prometheus_data="",
        loki_logs="",
        grafana_link="",
        final_result=None,
    )


def render_alert_info(alert_payload: Dict[str, Any]) -> str:
    alert = (alert_payload.get("alerts") or [{}])[0]
    labels = alert.get("labels", {})
    annotations = alert.get("annotations", {})
    name = labels.get("alertname", "Unknown Alert")
    service = labels.get("service", "Unknown Service")
    summary = annotations.get("summary", "No summary provided.")
    return f"Alert '{name}' for service '{service}': {summary}"


app = FastAPI(
    title="AIOps Diagnostic Agent Service",
    description="API for the MLOps Guard Agent, capable of diagnosing issues using Prometheus and Loki.",
)


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


@app.get("/")
async def read_root():
    logger.info("Received request to root endpoint.")
    return {"message": "AIOps Diagnostic Agent Service is running and ready to diagnose alerts!"}


def raise_rate_limited(endpoint: str, exc: LLMRateLimitError) -> None:
    AGENT_ERROR_COUNT.labels(endpoint=endpoint, error_type="LLMRateLimitError").inc()
    AGENT_DIAGNOSIS_COUNT.labels(outcome="rate_limited").inc()
    logger.error("Diagnosis aborted, LLM rate limited: %s", exc)
    raise HTTPException(status_code=429, detail=str(exc)) from exc


# Sync endpoint (def, not async def): FastAPI runs it in its thread pool, so a long
# diagnosis does not block the other requests (/metrics...).
@app.post("/diagnose_alert")
def diagnose_alert(alert_payload: Dict[str, Any] = Body(...)):
    AGENT_RUN_COUNT.inc()
    alert_info = render_alert_info(alert_payload)
    logger.info("Received alert for diagnosis: %s", alert_info)

    start_time = time.time()
    try:
        final_state, degraded_reason = invoke_diagnosis(DIAGNOSTIC_AGENT, build_initial_state(alert_info))
        if degraded_reason:
            # Step limit reached (AGENT_RECURSION_LIMIT): explicit degraded answer, not a 500.
            AGENT_DIAGNOSIS_COUNT.labels(outcome="degraded").inc()
            return {
                "status": "degraded",
                "reason": degraded_reason,
                "agent_diagnosis": degraded_diagnosis_message(final_state),
                "tools_called": tools_called(final_state.get("messages", [])),
            }
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
            "tools_called": tools_called(messages),
        }

    except LLMRateLimitError as exc:
        raise_rate_limited("/diagnose_alert", exc)

    except Exception as exc:
        AGENT_ERROR_COUNT.labels(endpoint="/diagnose_alert", error_type=type(exc).__name__).inc()
        AGENT_DIAGNOSIS_COUNT.labels(outcome="failed").inc()
        logger.exception("AIOps agent diagnosis failure")
        raise HTTPException(status_code=500, detail=f"Agent diagnostic failed: {exc}") from exc
    finally:
        duration = time.time() - start_time
        logger.info("Agent diagnostic run for alert took %.4f seconds.", duration)


@app.get("/metrics")
async def prometheus_metrics():
    return Response(content=generate_latest(), media_type="text/plain")


__all__ = ["app"]
