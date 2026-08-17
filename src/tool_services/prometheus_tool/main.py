import os
import logging
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from prometheus_client import Counter, Histogram, generate_latest
from fastapi.responses import Response, JSONResponse
import time

from tool import PrometheusQueryTool
from mcp_server import handle_mcp_request

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Metrics
REQUEST_COUNT = Counter("prometheus_tool_request_count", "Total request count", ["method", "endpoint", "http_status"])
REQUEST_LATENCY = Histogram("prometheus_tool_request_latency_seconds", "Request latency", ["method", "endpoint"])

app = FastAPI(title="Prometheus Tool Service")

@app.middleware("http")
async def monitor_requests(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    latency = time.time() - start_time
    REQUEST_COUNT.labels(method=request.method, endpoint=request.url.path, http_status=response.status_code).inc()
    REQUEST_LATENCY.labels(method=request.method, endpoint=request.url.path).observe(latency)
    return response

PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://prometheus:9090")
tool = PrometheusQueryTool(PROMETHEUS_URL)

class QueryRequest(BaseModel):
    query: str
    time_range_minutes: int = 5
    step_seconds: int = 30
    target_service: Optional[str] = None

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/query")
def query(request: QueryRequest):
    result = tool.query_range(request.query, request.time_range_minutes, request.step_seconds, request.target_service)
    return {"result": result}

def _run_tool(name: str, arguments: dict) -> str:
    # Single dispatch point: MCP names are prefixed, implementation is shared
    # with the legacy POST /query endpoint (tool.py is untouched).
    if name == "prometheus.query_range":
        return tool.query_range(
            arguments["query"],
            int(arguments.get("time_range_minutes", 5)),
            int(arguments.get("step_seconds", 30)),
            arguments.get("target_service"),
        )
    raise ValueError(f"Unknown tool: {name}")

@app.post("/mcp")
async def mcp(request: Request):
    """MCP 2026-07-28 stateless endpoint (coexists with legacy POST /query)."""
    body = await request.json()
    response_body, status = handle_mcp_request(body, dict(request.headers), _run_tool)
    return JSONResponse(content=response_body, status_code=status)

@app.get("/metrics")
def metrics():
    return Response(content=generate_latest(), media_type="text/plain")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
