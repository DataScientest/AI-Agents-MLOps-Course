import os
import random
import time
import logging
import uvicorn

from fastapi import FastAPI, Request, Response, HTTPException, Body
from prometheus_client import generate_latest, Counter, Histogram, Gauge
from typing import Dict, Any, List, Optional

from langchain_groq import ChatGroq
from langchain_core.tools import Tool
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

from state import AgentState
from agents.conditional_agent import create_alert_router_agent
from tools.mlops_tools import check_alert_severity, CheckAlertSeverityInput


# --- FastAPI App Initialization ---
app = FastAPI(
    title="AIOps Monitor Agent Service",
    description="API for the MLOps Guard Agent (Conditional Branching Pattern), exposing endpoints to receive alerts and metrics."
)

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Prometheus Metrics for the Agent Service ---
API_REQUEST_COUNT = Counter(
    'aiops_monitor_agent_api_requests_total', 'Total number of requests to the AIOps Monitor Agent API'
)
API_REQUEST_LATENCY_SECONDS = Histogram(
    'aiops_monitor_agent_api_request_latency_seconds', 'Latency of AIOps Monitor Agent API requests',
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)
AGENT_RUN_COUNT = Counter(
    'aiops_monitor_agent_runs_total', 'Total number of agent execution runs triggered'
)
AGENT_ERROR_COUNT = Counter(
    'aiops_monitor_agent_errors_total', 'Total number of agent execution errors', ['endpoint', 'error_type']
)
AGENT_STATUS_GAUGE = Gauge(
    'aiops_monitor_agent_status', 'Current operational status of the AIOps Monitor Agent (1=online, 0=offline)'
)
AGENT_ALERT_SEVERED_COUNT = Counter(
    'aiops_monitor_agent_alerts_processed_severity_total', 'Count of alerts processed by severity by the Monitor Agent', ['severity']
)

# Set initial agent status
AGENT_STATUS_GAUGE.set(1)

# --- LLM Initialization ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    logger.error("GROQ_API_KEY environment variable not set in AIOps Agent Service.")
    exit(1)

try:
    llm_for_deployed_agent = ChatGroq(
        temperature=0,
        model_name="llama-3.1-8b-instant",
        groq_api_key=GROQ_API_KEY
    )
    logger.info("LLM for deployed monitor agent initialized successfully.")
except Exception as e:
    logger.error(f"Error initializing LLM for deployed monitor agent: {e}")
    exit(1)

# --- Tools available to the deployed agent ---
deployed_agent_tools = [
    Tool(
        name="CheckAlertSeverity",
        func=check_alert_severity,
        description="Checks the severity of an alert description. Returns 'critical', 'medium' or 'low'.",
        args_schema=CheckAlertSeverityInput
    ),
]
logger.info(f"{len(deployed_agent_tools)} tools available to the deployed AIOps Monitor Agent.")

# --- Instantiate the LangGraph Agent ---
try:
    alert_router_agent_instance = create_alert_router_agent(llm_for_deployed_agent, deployed_agent_tools)
    logger.info("Conditional Branching AIOps Monitor Agent (LangGraph) instantiated successfully.")
except Exception as e:
    logger.error(f"Error instantiating LangGraph agent: {e}")
    exit(1)


# --- Middleware for request metrics ---
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    API_REQUEST_COUNT.inc()
    start_time = time.time()
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        AGENT_ERROR_COUNT.labels(endpoint=request.url.path, error_type=type(e).__name__).inc()
        logger.error(f"Unhandled API error: {e}", exc_info=True)
        raise
    finally:
        process_time = time.time() - start_time
        API_REQUEST_LATENCY_SECONDS.observe(process_time)
        logger.info(f"API Request to {request.url.path} took {process_time:.4f} seconds.")


# --- Endpoints ---
@app.get("/")
async def read_root():
    logger.info("Received request to root endpoint.")
    return {"message": "AIOps Monitor Agent Service is running and ready to receive alerts!"}

@app.post("/receive_alert")
async def receive_alert(alert_payload: Dict[str, Any] = Body(...)):
    """
    Receives an alert payload (e.g., from Prometheus AlertManager webhook)
    and triggers the AIOps agent to route it.
    """
    AGENT_RUN_COUNT.inc()
    alert_name = alert_payload.get("alerts", [{}])[0].get("labels", {}).get("alertname", "Unknown Alert")
    alert_summary = alert_payload.get("alerts", [{}])[0].get("annotations", {}).get("summary", "No summary provided.")
    
    alert_info = f"Alert '{alert_name}': {alert_summary}"

    logger.info(f"Received alert from external system: '{alert_info}'")
    
    start_agent_run_time = time.time()
    try:
        initial_state = AgentState(messages=[HumanMessage(content=f"Route this alert: {alert_info}")], alert_info=alert_info,
                                   proposed_action="", human_feedback="", system_metrics={}, report_content="",
                                   alert_severity="unknown", investigation_query="", investigation_step=0, max_investigation_steps=0, logs_found=False, final_result=None)
        final_state = alert_router_agent_instance.invoke(initial_state)
        agent_final_message = final_state['messages'][-1].content if final_state['messages'] else "No final message from agent."
        
        severity = final_state.get("alert_severity", "unknown")
        AGENT_ALERT_SEVERED_COUNT.labels(severity=severity).inc()
        
        logger.info(f"Agent run completed. Final status: {agent_final_message}")
        return {"status": "success", "agent_response": agent_final_message, "alert_severity": severity}

    except Exception as e:
        AGENT_ERROR_COUNT.labels(endpoint="/receive_alert", error_type=type(e).__name__).inc()
        logger.error(f"AIOps agent execution failure: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {e}")
    finally:
        agent_run_latency = time.time() - start_agent_run_time
        logger.info(f"Agent run for alert '{alert_info}' took {agent_run_latency:.4f} seconds.")

@app.get("/metrics")
async def prometheus_metrics():
    return Response(content=generate_latest(), media_type="text/plain")

# # --- Simulate periodic internal events for logging and status ---
# def periodic_internal_events():
#     while True:
#         time.sleep(random.uniform(15, 45)) # Every 15-45 seconds
#         if random.random() < 0.1:
#             logger.warning("AIOps Monitor Agent Service: Internal resource usage high warning.")
#         if random.random() < 0.05:
#             logger.error("AIOps Monitor Agent Service: Failed to connect to a dummy internal service.")
#             AGENT_STATUS_GAUGE.set(0) # Agent might go offline
#             time.sleep(random.uniform(5, 10)) # Stay offline for a bit
#             AGENT_STATUS_GAUGE.set(1) # Then come back online
#         logger.info("AIOps Monitor Agent Service: Performing routine self-check.")

# import threading
# threading.Thread(target=periodic_internal_events, daemon=True).start()
