import os
import logging
import requests
from pydantic import BaseModel, Field
from typing import Optional, Union
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

from config import (
    PROMETHEUS_TOOL_SERVICE_URL,
    LOKI_TOOL_SERVICE_URL,
    GRAFANA_TOOL_SERVICE_URL,
    SYSTEM_TOOL_SERVICE_URL,
    KNOWLEDGE_BASE_URL as KNOWLEDGE_BASE_SERVICE_URL,
)

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

@tool(args_schema=PrometheusQueryInput)
def PrometheusQuery(query: str, time_range_minutes: Union[int, str], step_seconds: Union[int, str], target_service: Optional[str] = None) -> str:
    """Executes a PromQL query via the Prometheus Tool Service."""
    logger.info(f"Agent Core calling Prometheus Tool Service: {query}")
    try:
        payload = {
            "query": query,
            "time_range_minutes": int(time_range_minutes),
            "step_seconds": int(step_seconds),
            "target_service": target_service
        }
        resp = requests.post(f"{PROMETHEUS_TOOL_SERVICE_URL}/query", json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json().get("result", "Error: No results.")
    except Exception as e:
        logger.error(f"Prometheus tool call failed: {e}")
        return f"Error: {e}"

@tool(args_schema=LokiLogSearchInput)
def LokiLogSearch(query: str, time_range_minutes: Union[int, str], limit: Union[int, str], target_service: Optional[str] = None) -> str:
    """Executes a LogQL search via the Loki Tool Service."""
    logger.info(f"Agent Core calling Loki Tool Service: {query}")
    try:
        payload = {
            "query": query,
            "time_range_minutes": int(time_range_minutes),
            "limit": int(limit),
            "target_service": target_service
        }
        resp = requests.post(f"{LOKI_TOOL_SERVICE_URL}/search", json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json().get("result", "Error: No results.")
    except Exception as e:
        logger.error(f"Loki tool call failed: {e}")
        return f"Error: {e}"

@tool(args_schema=GrafanaDashboardLinkInput)
def GrafanaDashboardLink(dashboard_uid: str, time_range_minutes: Union[int, str], service_filter: Optional[str] = None) -> str:
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
