import os
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from prometheus_client import Counter, Histogram, generate_latest
from fastapi.responses import Response

from tool import SystemMetricsTool

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="System Tool Service", description="Microservice for fetching system-level metrics.")

# Metrics
REQUEST_COUNT = Counter('system_tool_requests_total', 'Total requests to System Tool', ['method', 'endpoint'])
REQUEST_LATENCY = Histogram('system_tool_request_latency_seconds', 'Latency of System Tool requests')

PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://prometheus:9090")
system_tool = SystemMetricsTool(PROMETHEUS_URL)

class SystemMetricsRequest(BaseModel):
    component: str
    target_service: Optional[str] = None

@app.get("/health")
def health():
    return {"status": "ok", "service": "system-tool-service"}

@app.get("/ready")
def ready():
    return {"status": "ready"}

@app.post("/system_metrics")
def get_system_metrics(request: SystemMetricsRequest):
    REQUEST_COUNT.labels(method='POST', endpoint='/system_metrics').inc()
    with REQUEST_LATENCY.time():
        logger.info(f"Received request for {request.component} metrics")
        result = system_tool.get_metrics(request.component, request.target_service)
        return {"result": result}

@app.get("/metrics")
def metrics():
    return Response(content=generate_latest(), media_type="text/plain")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
