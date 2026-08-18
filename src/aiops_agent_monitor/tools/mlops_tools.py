import os
import logging
import requests
from pydantic import BaseModel, Field
from typing import Optional, Union
from langchain_core.tools import tool

from tools import mcp_client

logger = logging.getLogger(__name__)

import time
from config import (
    PROMETHEUS_TOOL_SERVICE_URL,
    LOKI_TOOL_SERVICE_URL,
    GRAFANA_TOOL_SERVICE_URL,
    SYSTEM_TOOL_SERVICE_URL,
    KNOWLEDGE_BASE_URL as KNOWLEDGE_BASE_SERVICE_URL,
)

class CircuitBreaker:
    def __init__(self, name: str, failure_threshold: int = 3, recovery_timeout: int = 30):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF-OPEN
        self.last_failure_time = 0

    def get_effective_state(self) -> str:
        """
        Get the effective state, checking if OPEN should transition to HALF-OPEN.
        Used by gateway to determine if requests should be allowed through.
        """
        if self.state == "OPEN" and time.time() - self.last_failure_time > self.recovery_timeout:
            return "HALF-OPEN"
        return self.state

    def is_blocking(self) -> bool:
        """
        Returns True if circuit should block requests.
        OPEN blocks, HALF-OPEN allows (to test recovery), CLOSED allows.
        """
        return self.get_effective_state() == "OPEN"

    def call(self, func, *args, **kwargs):
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF-OPEN"
                logger.info(f"Circuit Breaker [{self.name}] transition to HALF-OPEN")
            else:
                raise Exception(f"{self.name} Service Unavailable (Circuit Breaker Open)")

        try:
            result = func(*args, **kwargs)
            if self.state == "HALF-OPEN":
                self.state = "CLOSED"
                self.failures = 0
                logger.info(f"Circuit Breaker [{self.name}] transition to CLOSED")
            return result
        except Exception as e:
            self.failures += 1
            self.last_failure_time = time.time()
            if self.failures >= self.failure_threshold:
                self.state = "OPEN"
                logger.warn(f"Circuit Breaker [{self.name}] transition to OPEN")
            raise e

# Initialize breakers
loki_breaker = CircuitBreaker("Loki", failure_threshold=3)
prom_breaker = CircuitBreaker("Prometheus", failure_threshold=3)
kb_breaker = CircuitBreaker("KnowledgeBase", failure_threshold=3)
system_breaker = CircuitBreaker("System", failure_threshold=3)

# --- Pydantic Models for Tool Inputs ---

class PrometheusQueryInput(BaseModel):
    query: str = Field(description="The PromQL query to execute on Prometheus, e.g., 'rate(node_cpu_seconds_total[5m])'.")
    time_range_minutes: Union[int, str] = Field(default=5, description="The time range in minutes for the query.")
    step_seconds: Union[int, str] = Field(default=30, description="The query resolution step width in seconds.")
    target_service: Optional[str] = Field(default=None, description="The specific service to filter metrics for, e.g., 'news-classifier-api'.")

class LokiLogSearchInput(BaseModel):
    query: str = Field(description="The LogQL query to execute on Loki, e.g., '{job=\"docker\", container_name=\"news-classifier-api\"} |= \"error\"'.")
    time_range_minutes: Union[int, str] = Field(default=5, description="The time range in minutes for the query.")
    limit: Union[int, str] = Field(default=10, description="Maximum number of log lines to return.")
    target_service: Optional[str] = Field(default=None, description="The specific service to filter logs for, e.g., 'news-classifier-api'.")

class GrafanaDashboardLinkInput(BaseModel):
    dashboard_uid: str = Field(description="The UID of the Grafana dashboard to link to.")
    time_range_minutes: Union[int, str] = Field(default=60, description="The time range in minutes for the dashboard link.")
    service_filter: Optional[str] = Field(default=None, description="Optional service name to filter the dashboard.")

class SystemMetricsInput(BaseModel):
    component: str = Field(description="The system component to check metrics for, e.g., 'CPU', 'Memory', 'Disk'.")
    target_service: Optional[str] = Field(default=None, description="The specific service to filter metrics for, e.g., 'news-classifier-api'.")

class RAGKnowledgeSearchInput(BaseModel):
    query: str = Field(description="The query describing the current incident, e.g., 'high CPU usage after deployment'.")
    service_name: Optional[str] = Field(default=None, description="Filter results to specific service, e.g., 'news-classifier-api'.")
    alert_type: Optional[str] = Field(default=None, description="Filter results to specific alert type, e.g., 'HighCPULoad'.")

# --- Tool Wrappers (HTTP Proxies) ---

# Chapter 6 (MCP): switch the Prometheus tool transport without touching the
# agent graph. "http" = legacy Chapter 5 proxy, "mcp" = MCP 2026-07-28 endpoint.
PROMETHEUS_TRANSPORT = os.getenv("PROMETHEUS_TRANSPORT", "http")

@tool(args_schema=PrometheusQueryInput)
def PrometheusQuery(query: str, time_range_minutes: Union[int, str] = 5, step_seconds: Union[int, str] = 30, target_service: Optional[str] = None) -> str:
    """Executes a PromQL query via the Prometheus Tool Service."""
    logger.info(f"Agent Core calling Prometheus Tool Service ({PROMETHEUS_TRANSPORT}): {query}")
    def _perform_query():
        payload = {
            "query": query,
            "time_range_minutes": int(time_range_minutes),
            "step_seconds": int(step_seconds),
            "target_service": target_service
        }
        if PROMETHEUS_TRANSPORT == "mcp":
            return mcp_client.call_tool(
                PROMETHEUS_TOOL_SERVICE_URL, "prometheus.query_range", payload, timeout=30
            )
        resp = requests.post(f"{PROMETHEUS_TOOL_SERVICE_URL}/query", json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json().get("result", "Error: No results.")

    try:
        return prom_breaker.call(_perform_query)
    except Exception as e:
        logger.error(f"Prometheus tool call failed: {e}")
        return f"Error: {e}"

@tool(args_schema=LokiLogSearchInput)
def LokiLogSearch(query: str, time_range_minutes: Union[int, str] = 5, limit: Union[int, str] = 10, target_service: Optional[str] = None) -> str:
    """Executes a LogQL search via the Loki Tool Service."""
    logger.info(f"Agent Core calling Loki Tool Service: {query}")
    def _perform_search():
        payload = {
            "query": query,
            "time_range_minutes": int(time_range_minutes),
            "limit": int(limit),
            "target_service": target_service
        }
        resp = requests.post(f"{LOKI_TOOL_SERVICE_URL}/search", json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json().get("result", "Error: No results.")

    try:
        return loki_breaker.call(_perform_search)
    except Exception as e:
        logger.error(f"Loki tool call failed: {e}")
        return f"Error: {e}"

@tool(args_schema=GrafanaDashboardLinkInput)
def GrafanaDashboardLink(dashboard_uid: str, time_range_minutes: Union[int, str] = 60, service_filter: Optional[str] = None) -> str:
    """Generates a Grafana dashboard link via the Grafana Tool Service."""
    logger.info(f"Agent Core calling Grafana Tool Service: {dashboard_uid}")
    try:
        payload = {
            "dashboard_uid": dashboard_uid,
            "time_range_minutes": int(time_range_minutes),
            "service_filter": service_filter
        }
        resp = requests.post(f"{GRAFANA_TOOL_SERVICE_URL}/link", json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json().get("result", "Error: No results.")
    except Exception as e:
        logger.error(f"Grafana tool call failed: {e}")
        return f"Error: {e}"

@tool(args_schema=SystemMetricsInput)
def SystemMetrics(component: str, target_service: Optional[str] = None) -> str:
    """Fetches system metrics (CPU, Memory, Disk) via the System Tool Service."""
    logger.info(f"Agent Core calling System Tool Service: {component}")
    try:
        payload = {"component": component, "target_service": target_service}
        resp = requests.post(f"{SYSTEM_TOOL_SERVICE_URL}/system_metrics", json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json().get("result", "Error: No results.")
    except Exception as e:
        logger.error(f"System tool call failed: {e}")
        return f"Error: {e}"

@tool(args_schema=RAGKnowledgeSearchInput)
def RAGKnowledgeSearch(query: str, service_name: Optional[str] = None, alert_type: Optional[str] = None) -> str:
    """Searches the knowledge base for similar past incidents via the Knowledge Base Service."""
    logger.info(f"Agent Core calling KB Service: {query}")
    try:
        payload = {
            "query": query,
            "service_name": service_name,
            "alert_type": alert_type,
            "top_k": 3,
            "similarity_threshold": 0.7
        }
        resp = requests.post(f"{KNOWLEDGE_BASE_SERVICE_URL}/search", json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        
        results = data.get("results", [])
        if not results:
            return "No similar incidents found in knowledge base."
            
        summary = f"Found {len(results)} similar incidents:\n\n"
        for i, res in enumerate(results, 1):
            inc = res['incident']
            summary += f"--- Incident {i} (Similarity: {res['similarity_score']:.2f}) ---\n"
            summary += f"Summary: {inc['summary']}\n"
            summary += f"Root Cause: {inc['root_cause']}\n"
            summary += f"Solution: {inc['solution']}\n\n"
        return summary
    except Exception as e:
        logger.error(f"KB tool search failed: {e}")
        return f"Error: {e}"
