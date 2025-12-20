import os
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from prometheus_client import Counter, Histogram, generate_latest
from fastapi.responses import Response

from tool import LokiLogSearchTool

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="Loki Tool Service")

LOKI_URL = os.getenv("LOKI_URL", "http://loki:3100")
tool = LokiLogSearchTool(LOKI_URL)

class SearchRequest(BaseModel):
    query: str
    time_range_minutes: int = 5
    limit: int = 10
    target_service: Optional[str] = None

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/search")
def search(request: SearchRequest):
    result = tool.search(request.query, request.time_range_minutes, request.limit, request.target_service)
    return {"result": result}

@app.get("/metrics")
def metrics():
    return Response(content=generate_latest(), media_type="text/plain")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
