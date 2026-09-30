import pytest
import requests
import subprocess
import time
import os
import threading

def stop_service(service_name):
    print(f"Stopping service: {service_name}...")
    # Go up 2 levels from tests/chaos to reach root
    compose_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../docker-compose.yml"))
    subprocess.run(["docker", "compose", "-f", compose_path, "stop", service_name], check=True)

def start_service(service_name):
    print(f"Starting service: {service_name}...")
    compose_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../docker-compose.yml"))
    subprocess.run(["docker", "compose", "-f", compose_path, "start", service_name], check=True)

def post_ignoring_errors(url, payload):
    """Send a diagnosis that is expected to fail (used as a failure trigger)."""
    try:
        requests.post(url, json=payload, timeout=120)
    except Exception as e:
        print(f"  Request failed as expected: {type(e).__name__}")

def get_prometheus_breaker(agent_url):
    """Return the Prometheus circuit breaker state exposed by the Agent Core."""
    cb_resp = requests.get(f"{agent_url}/circuit_breakers", timeout=5)
    cb_resp.raise_for_status()
    data = cb_resp.json()
    return data["breakers"]["prometheus"], data.get("critical_service_unavailable", False)

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
    3. Trigger failures until the circuit breaker opens (threshold=3)
    4. Right after it opens, verify gateway fails fast with 503 (not timeout)
    5. Restart service and verify recovery

    Timing: the circuit stays OPEN for recovery_timeout (30s) after the LAST failure,
    then becomes HALF-OPEN and lets one request through. A diagnosis can take longer
    than that (LLM rate-limit retries), so the test checks the gateway as soon as the
    circuit opens instead of after a fixed number of diagnoses.
    """
    gateway_url = service_urls["gateway"]
    agent_url = service_urls["agent"]
    prometheus_service_name = "prometheus-tool-service"
    gateway_cache_ttl = 3  # the gateway caches /circuit_breakers for 2s

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

        # 3. Trigger failures until the circuit breaker is OPEN and blocking.
        # Threshold is 3 failures (configured in mlops_tools.py); each diagnosis usually
        # makes at least one Prometheus call. Each diagnosis runs in a background thread
        # while the test polls /circuit_breakers, so step 4 starts right after the failure
        # that opened the circuit, however long the diagnosis itself takes.
        print("\n✓ Step 3: Triggering failures to trip circuit breaker...")
        blocking = False
        for i in range(6):
            print(f"  Failure trigger {i+1}...")
            trigger = threading.Thread(
                target=post_ignoring_errors,
                args=(f"{gateway_url}/diagnose_alert", sample_alert),
                daemon=True,
            )
            trigger.start()
            while trigger.is_alive() and not blocking:
                _, blocking = get_prometheus_breaker(agent_url)
                time.sleep(0.5)
            breaker, blocking = get_prometheus_breaker(agent_url)
            print(f"  Prometheus breaker: {breaker}")
            if blocking:
                break

        # 4. Verify fail-fast behavior at gateway level, while the circuit is still OPEN
        print("\n✓ Step 4: Verifying gateway fail-fast behavior...")
        assert breaker["state"] == "OPEN", f"Expected Prometheus circuit to be OPEN, got: {breaker}"
        assert blocking, f"Prometheus circuit is not blocking requests: {breaker}"

        # Let the gateway cache (2s TTL) see the OPEN state, then check the 503
        time.sleep(gateway_cache_ttl)
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
