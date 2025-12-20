import os
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from prometheus_client import Counter, Histogram, generate_latest
from fastapi.responses import Response

from tool import PrometheusQueryTool

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="Prometheus Tool Service")

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

@app.get("/metrics")
def metrics():
    return Response(content=generate_latest(), media_type="text/plain")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
