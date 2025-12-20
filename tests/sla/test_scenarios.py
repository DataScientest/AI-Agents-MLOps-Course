import pytest
import requests
import time
import json

# SLA Definitions
SLA_MAX_LATENCY_P95 = 120.0 # seconds
SLA_MIN_ACCURACY = 0.85 # 85%
SLA_MIN_AVAILABILITY = 0.995 # 99.5%

SCENARIOS = [
    {
        "id": "cpu_spike",
        "name": "Scenario 1: High CPU Alert",
        "alert": {
            "labels": {
                "alertname": "HighCPUUsage",
                "service": "news-api",
                "severity": "critical",
                "instance": "instance-1"
            },
            "annotations": {
                "summary": "CPU usage > 90% on instance-1",
                "description": "CPU usage is critically high"
            }
        },
        "expected_keywords": ["cpu", "load", "process", "high"]
    },
    {
        "id": "memory_leak",
        "name": "Scenario 2: Memory Leak",
        "alert": {
            "labels": {
                "alertname": "MemoryLeak",
                "service": "database",
                "severity": "warning",
                "instance": "db-01"
            },
            "annotations": {
                "summary": "Memory usage increasing steadily",
                "description": "Potential memory leak detected"
            }
        },
        "expected_keywords": ["memory", "leak", "oom", "heap"]
    }
    # Add more scenarios as needed
]

@pytest.mark.parametrize("scenario", SCENARIOS)
def test_sla_compliance(service_urls, scenario):
    """
    Validate that a specific scenario meets the production SLA:
    - Successful diagnosis
    - Latency <= SLA_MAX_LATENCY_P95
    - Correct keywords in diagnosis (proxy for accuracy)
    """
    gateway_url = service_urls["gateway"]
    
    # Wrap alert in Prometheus webhook format
    alert_payload = {
        "alerts": [scenario["alert"]]
    }
    
    start_time = time.time()
    response = requests.post(f"{gateway_url}/diagnose_alert", json=alert_payload, timeout=180)
    latency = time.time() - start_time
    
    # 1. Availability/Success Check
    assert response.status_code == 200, f"Scenario {scenario['id']} failed with status {response.status_code}"
    
    data = response.json()
    diagnosis = data.get("agent_diagnosis", "").lower()
    
    # 2. Latency Check
    assert latency <= SLA_MAX_LATENCY_P95, f"Scenario {scenario['id']} took {latency:.2f}s, exceeding SLA of {SLA_MAX_LATENCY_P95}s"
    
    # 3. Accuracy/Content Check
    found_keywords = [kw for kw in scenario["expected_keywords"] if kw in diagnosis]
    assert len(found_keywords) > 0, f"Scenario {scenario['id']} diagnosis did not contain expected keywords. Found: {diagnosis}"
    
    print(f"\nScenario {scenario['id']} PASSED: latency={latency:.2f}s, keywords={found_keywords}")
