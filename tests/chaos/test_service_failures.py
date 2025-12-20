import pytest
import requests
import subprocess
import time
import os

def stop_service(service_name):
    print(f"Stopping service: {service_name}...")
    # Go up 2 levels from tests/chaos to reach root
    compose_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../docker-compose.yml"))
    subprocess.run(["docker", "compose", "-f", compose_path, "stop", service_name], check=True)

def start_service(service_name):
    print(f"Starting service: {service_name}...")
    compose_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../docker-compose.yml"))
    subprocess.run(["docker", "compose", "-f", compose_path, "start", service_name], check=True)

def test_circuit_breaker_prometheus_failure(service_urls, sample_alert):
    """
    Validate circuit breaker opens when Prometheus tool service fails.
    1. Verify happy path.
    2. Stop Prometheus service.
    3. Trigger failures to open circuit.
    4. Verify fail-fast behavior.
    5. Restart and verify recovery.
    """
    gateway_url = service_urls["gateway"]
    prometheus_service_name = "prometheus-tool-service"

    try:
        # 1. Happy path
        print("\nChecking happy path...")
        resp = requests.post(f"{gateway_url}/diagnose_alert", json=sample_alert, timeout=120)
        assert resp.status_code == 200

        # 2. Stop service
        stop_service(prometheus_service_name)
        time.sleep(2) # Wait for service to be fully down

        # 3. Trigger failures to trip the circuit breaker
        # Assuming threshold is 3 failures in Chapter 5 implementation
        print("Triggering failures to trip circuit breaker...")
        for i in range(3):
            try:
                requests.post(f"{gateway_url}/diagnose_alert", json=sample_alert, timeout=20)
            except Exception:
                pass
        
        # 4. Verify fail-fast behavior
        # After the circuit is open, requests should fail immediately
        print("Verifying fail-fast behavior...")
        start_time = time.time()
        resp = requests.post(f"{gateway_url}/diagnose_alert", json=sample_alert, timeout=5)
        duration = time.time() - start_time
        
        # Circuit breaker should return a 503 or 500 quickly, or the request should fail fast
        assert duration < 2.0 # Should be much faster than a 10s timeout
        assert resp.status_code in [503, 500]
        assert "circuit" in resp.text.lower() or "fail-fast" in resp.text.lower() or "error" in resp.text.lower()

    finally:
        # 5. Restart and verify recovery (if needed by other tests)
        start_service(prometheus_service_name)
        print("Waiting for recovery...")
        time.sleep(10) # Wait for health checks to pass and circuit to half-open/close
        
        # Verify recovery
        resp = requests.post(f"{gateway_url}/diagnose_alert", json=sample_alert, timeout=120)
        assert resp.status_code == 200
