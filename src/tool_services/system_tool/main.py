import os
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from prometheus_client import Counter, Histogram, generate_latest
from fastapi.responses import Response
import time

from tool import SystemMetricsTool

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="System Tool Service", description="Microservice for fetching system-level metrics.")

# Metrics
REQUEST_COUNT = Counter('system_tool_requests_total', 'Total requests to System Tool', ['method', 'endpoint', 'http_status'])
REQUEST_LATENCY = Histogram('system_tool_request_latency_seconds', 'Latency of System Tool requests', ['method', 'endpoint'])

@app.middleware("http")
async def monitor_requests(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    latency = time.time() - start_time
    REQUEST_COUNT.labels(method=request.method, endpoint=request.url.path, http_status=response.status_code).inc()
    REQUEST_LATENCY.labels(method=request.method, endpoint=request.url.path).observe(latency)
    return response

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
    logger.info(f"Received request for {request.component} metrics")
    result = system_tool.get_metrics(request.component, request.target_service)
    return {"result": result}

@app.get("/metrics")
def metrics():
    return Response(content=generate_latest(), media_type="text/plain")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
