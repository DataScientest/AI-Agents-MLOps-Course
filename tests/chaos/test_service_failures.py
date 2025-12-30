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
    
    Production pattern tested:
    1. Agent Core tracks circuit breaker state per tool service
    2. Agent Core exposes /circuit_breakers endpoint
    3. API Gateway checks circuit state BEFORE forwarding requests
    4. Gateway returns 503 immediately when critical circuit is open
    
    Steps:
    1. Verify happy path works
    2. Stop Prometheus service
    3. Trigger failures to trip the circuit breaker (threshold=3)
    4. Verify gateway fails fast with 503 (not timeout)
    5. Restart service and verify recovery
    """
    gateway_url = service_urls["gateway"]
    agent_url = service_urls["agent"]
    prometheus_service_name = "prometheus-tool-service"

    try:
        # 1. Happy path - verify system works normally
        print("\n✓ Step 1: Checking happy path...")
        resp = requests.post(f"{gateway_url}/diagnose_alert", json=sample_alert, timeout=120)
        assert resp.status_code == 200, f"Happy path failed: {resp.status_code}"
        print(f"  Happy path succeeded in {resp.elapsed.total_seconds():.2f}s")

        # 2. Stop Prometheus service
        print("\n✓ Step 2: Stopping Prometheus service...")
        stop_service(prometheus_service_name)
        time.sleep(3)  # Wait for service to be fully down

        # 3. Trigger failures to trip the circuit breaker
        # Circuit breaker threshold is 3 failures (configured in mlops_tools.py)
        print("\n✓ Step 3: Triggering failures to trip circuit breaker...")
        for i in range(4):  # 4 requests to ensure circuit opens
            try:
                print(f"  Failure trigger {i+1}/4...")
                requests.post(f"{gateway_url}/diagnose_alert", json=sample_alert, timeout=60)
            except Exception as e:
                print(f"  Request {i+1} failed as expected: {type(e).__name__}")
        
        # Small delay for circuit state to propagate to gateway cache
        time.sleep(3)
        
        # 4. Verify fail-fast behavior at gateway level
        # After circuit opens, gateway should return 503 immediately
        print("\n✓ Step 4: Verifying gateway fail-fast behavior...")
        
        # First check the circuit breaker state directly
        cb_resp = requests.get(f"{agent_url}/circuit_breakers", timeout=5)
        if cb_resp.status_code == 200:
            cb_state = cb_resp.json()
            print(f"  Circuit breaker state: {cb_state}")
            assert cb_state.get("critical_service_unavailable", False), \
                f"Expected Prometheus circuit to be OPEN, got: {cb_state}"
        
        # Now verify gateway returns 503 fast
        start_time = time.time()
        resp = requests.post(f"{gateway_url}/diagnose_alert", json=sample_alert, timeout=10)
        duration = time.time() - start_time
        
        print(f"  Gateway response: {resp.status_code} in {duration:.2f}s")
        print(f"  Response body: {resp.text[:200]}...")
        
        # Circuit breaker should cause gateway to return 503 in <2s
        assert duration < 2.0, f"Request took {duration:.2f}s - circuit breaker not failing fast!"
        assert resp.status_code == 503, f"Expected 503, got {resp.status_code}"
        assert "circuit" in resp.text.lower() or "unavailable" in resp.text.lower(), \
            f"Response should mention circuit breaker: {resp.text}"
        
        print(f"  ✓ Gateway failed fast in {duration:.2f}s with 503")

    finally:
        # 5. Restart and verify recovery
        print("\n✓ Step 5: Restarting Prometheus service...")
        start_service(prometheus_service_name)
        print("  Waiting for recovery (circuit half-open -> closed)...")
        time.sleep(35)  # Wait for recovery_timeout (30s) + health checks
        
        # Verify recovery - may need multiple attempts as circuit transitions
        print("  Verifying recovery...")
        for attempt in range(3):
            resp = requests.post(f"{gateway_url}/diagnose_alert", json=sample_alert, timeout=120)
            if resp.status_code == 200:
                print(f"  ✓ Service recovered on attempt {attempt+1}")
                break
            print(f"  Attempt {attempt+1}: status={resp.status_code}, retrying...")
            time.sleep(5)
        
        assert resp.status_code == 200, f"Service did not recover: {resp.status_code}"
