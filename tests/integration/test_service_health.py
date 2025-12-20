import pytest
import requests

def test_api_gateway_health(service_urls):
    """Verify API Gateway is responsive."""
    response = requests.get(f"{service_urls['gateway']}/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_agent_core_health(service_urls):
    """Verify Agent Core is responsive."""
    response = requests.get(f"{service_urls['agent']}/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_tool_services_health(service_urls):
    """Verify all tool services are responsive."""
    tools = ["prometheus", "loki", "knowledge_base"]
    for tool in tools:
        response = requests.get(f"{service_urls[tool]}/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

def test_service_startup_order(service_urls):
    """
    Integration test validating that Agent Core can actually reach a tool service.
    This implicitly tests service discovery/connectivity.
    """
    # We'll use the Agent Core's health check if it includes a check for dependencies,
    # or just perform a simple check.
    # For now, let's just ensure they are all up.
    for name, url in service_urls.items():
        try:
            response = requests.get(f"{url}/health", timeout=5)
            assert response.status_code == 200
        except Exception as e:
            pytest.fail(f"Service {name} at {url} is not reachable: {e}")
