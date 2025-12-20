import pytest
import os
import requests
import time
import json
from typing import Dict, Any

# Service URLs from environment or defaults
API_GATEWAY_URL = os.getenv("API_GATEWAY_URL", "http://localhost:8000")
AGENT_CORE_URL = os.getenv("AGENT_CORE_URL", "http://localhost:8005")
PROMETHEUS_TOOL_URL = os.getenv("PROMETHEUS_TOOL_URL", "http://localhost:8001")
LOKI_TOOL_URL = os.getenv("LOKI_TOOL_URL", "http://localhost:8002")
KNOWLEDGE_BASE_URL = os.getenv("KNOWLEDGE_BASE_URL", "http://localhost:8006")

@pytest.fixture(scope="session")
def service_urls() -> Dict[str, str]:
    return {
        "gateway": API_GATEWAY_URL,
        "agent": AGENT_CORE_URL,
        "prometheus": PROMETHEUS_TOOL_URL,
        "loki": LOKI_TOOL_URL,
        "knowledge_base": KNOWLEDGE_BASE_URL
    }

@pytest.fixture(scope="session")
def sample_alert() -> Dict[str, Any]:
    return {
        "alerts": [{
            "labels": {
                "alertname": "HighCPUUsage",
                "service": "news-classifier",
                "severity": "critical",
                "instance": "prod-server-01"
            },
            "annotations": {
                "summary": "CPU usage is above 90% for more than 5 minutes",
                "description": "CPU usage is above 90%"
            }
        }]
    }

@pytest.fixture(scope="session")
def wait_for_services(service_urls):
    """Wait for all services to be healthy before running tests."""
    timeout = 60
    start_time = time.time()
    
    for name, url in service_urls.items():
        health_url = f"{url}/health"
        if name == "loki": # Loki tool service might have a different health endpoint or we just check connectivity
            health_url = f"{url}/health"
            
        success = False
        while time.time() - start_time < timeout:
            try:
                response = requests.get(health_url, timeout=2)
                if response.status_code == 200:
                    success = True
                    break
            except requests.exceptions.RequestException:
                pass
            time.sleep(1)
        
        if not success:
            pytest.fail(f"Service {name} at {url} did not become healthy within {timeout}s")

@pytest.fixture
def mock_prometheus_response():
    """Returns a factory for mock Prometheus range query responses."""
    def _create_response(values=None, status="success"):
        if values is None:
            values = [["1700000000", "0.95"], ["1700000030", "0.98"]]
        return {
            "status": status,
            "data": {
                "resultType": "matrix",
                "result": [
                    {
                        "metric": {"__name__": "cpu_usage", "instance": "localhost:9090"},
                        "values": values
                    }
                ]
            }
        }
    return _create_response
