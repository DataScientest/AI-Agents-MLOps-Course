import os
import logging
import requests
from fastapi import FastAPI, HTTPException, Body, Request, Response
from pydantic import BaseModel
from typing import Dict, Any, List
import time
from prometheus_client import Counter, Histogram, generate_latest
from fastapi.responses import Response as FAResponse

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="AIOps API Gateway", description="Unified entry point for the AIOps Platform.")

# Metrics
REQUEST_COUNT = Counter('gateway_requests_total', 'Total requests to API Gateway', ['method', 'endpoint', 'http_status'])
REQUEST_LATENCY = Histogram('gateway_request_latency_seconds', 'Latency of API Gateway requests', ['method', 'endpoint'])

@app.middleware("http")
async def monitor_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    latency = time.time() - start_time
    REQUEST_COUNT.labels(method=request.method, endpoint=request.url.path, http_status=response.status_code).inc()
    REQUEST_LATENCY.labels(method=request.method, endpoint=request.url.path).observe(latency)
    return response

# Configuration
AGENT_CORE_SERVICE_URL = os.getenv("AGENT_CORE_SERVICE_URL", "http://aiops-agent-monitor:8005/diagnose_alert")

@app.get("/health")
def health():
    return {"status": "ok", "service": "api-gateway"}

@app.get("/health/mesh")
def health_mesh():
    services = {
        "agent-core": "http://aiops-agent-monitor:8005/health",
        "prometheus-service": "http://prometheus-tool-service:8001/health",
        "loki-service": "http://loki-tool-service:8002/health",
        "grafana-service": "http://grafana-tool-service:8003/health",
        "system-service": "http://system-tool-service:8004/health",
        "knowledge-base-service": "http://knowledge-base-service:8006/health",
    }
    
    health_results = {"api-gateway": "ok"}
    for name, url in services.items():
        try:
            resp = requests.get(url, timeout=2)
            if resp.status_code == 200:
                health_results[name] = resp.json().get("status", "ok")
            else:
                health_results[name] = f"error ({resp.status_code})"
        except Exception as e:
            health_results[name] = f"unreachable ({str(e)})"
            
    return health_results

@app.get("/ready")
def ready():
    try:
        # Check if agent core is ready (stripping the /diagnose_alert part for the healthy check if possible, but let's just check the base URL)
        base_url = AGENT_CORE_SERVICE_URL.rsplit('/', 1)[0]
        response = requests.get(f"{base_url}/ready", timeout=5)
        if response.status_code == 200:
            return {"status": "ready", "agent_core_status": "ok"}
        else:
            return {"status": "not_ready", "agent_core_status": f"unhealthy ({response.status_code})"}
    except Exception as e:
        return {"status": "not_ready", "agent_core_status": f"unreachable ({str(e)})"}

@app.post("/diagnose_alert")
async def diagnose_alert(payload: Dict[str, Any] = Body(...)):
    logger.info(f"Forwarding diagnostic request to Agent Core: {AGENT_CORE_SERVICE_URL}")
    try:
        response = requests.post(AGENT_CORE_SERVICE_URL, json=payload, timeout=120)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error communicating with Agent Core: {e}")
        raise HTTPException(status_code=502, detail=f"Bad Gateway: Error communicating with Agent Core: {e}")

@app.get("/metrics")
def metrics():
    return FAResponse(content=generate_latest(), media_type="text/plain")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
