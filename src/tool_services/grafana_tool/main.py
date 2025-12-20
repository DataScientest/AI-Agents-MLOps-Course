import os
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from prometheus_client import Counter, Histogram, generate_latest
from fastapi.responses import Response

from tool import GrafanaDashboardLinkTool

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="Grafana Tool Service")

# Use external URL if provided, otherwise default to internal
GRAFANA_URL = os.getenv("GRAFANA_URL", "http://localhost:3000")
tool = GrafanaDashboardLinkTool(GRAFANA_URL)

class LinkRequest(BaseModel):
    dashboard_uid: str
    time_range_minutes: int = 60
    service_filter: Optional[str] = None

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/link")
def get_link(request: LinkRequest):
    result = tool.get_link(request.dashboard_uid, request.time_range_minutes, request.service_filter)
    return {"result": result}

@app.get("/metrics")
def metrics():
    return Response(content=generate_latest(), media_type="text/plain")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
