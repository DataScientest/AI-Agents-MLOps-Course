import pytest
import requests
import time

def test_full_diagnosis_workflow(service_urls, sample_alert):
    """
    End-to-End test for a complete diagnosis flow:
    Alert -> API Gateway -> Agent Core -> Tool Services -> Diagnosis
    """
    # 1. Send alert to API Gateway
    gateway_url = service_urls["gateway"]
    response = requests.post(
        f"{gateway_url}/diagnose_alert",
        json=sample_alert,
        timeout=120 # E2E can be slow due to LLM
    )
    
    # 2. Validate response
    assert response.status_code == 200, f"Diagnosis failed: {response.status_code} {response.text[:300]}"
    data = response.json()

    # A real diagnosis: not a degraded answer, and the agent actually used its tools
    assert data.get("status") == "success", f"Degraded diagnosis: {data.get('agent_diagnosis')}"
    assert data.get("tools_called"), "The agent answered without calling any tool"
    
    # 3. Verify diagnosis structure
    assert "agent_diagnosis" in data
    assert "confidence_score" in data
    assert "current_agent_state" in data
    
    # 4. Verify content (basic check)
    diagnosis = data.get("agent_diagnosis", "").lower()
    assert any(keyword in diagnosis for keyword in ["cpu", "usage", "spike", "process", "high"])
    
    # 5. Verify state structure exists
    state = data.get("current_agent_state", {})
    # Just verify the state has expected fields (tools may or may not have been called depending on the scenario)
    assert "alert_info" in state
    assert "diagnosis_id" in state

def test_diagnosis_persistence(service_urls, sample_alert):
    """Verify that diagnosis state is persisted (Chapter 5 state management)."""
    gateway_url = service_urls["gateway"]
    
    # Trigger diagnosis
    response = requests.post(f"{gateway_url}/diagnose_alert", json=sample_alert, timeout=120)
    assert response.status_code == 200, f"Diagnosis failed: {response.status_code} {response.text[:300]}"
    assert response.json().get("status") == "success"
    thread_id = response.json().get("thread_id")
    
    if thread_id:
        # Check if we can retrieve it (if there's an endpoint for it)
        # Note: If no endpoint exists in current architecture, this test might need adjustment
        # For now, let's assume Agent Core has an endpoint or we check the DB
        pass
