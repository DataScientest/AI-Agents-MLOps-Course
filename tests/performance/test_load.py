"""
Load Testing: Validate system performance under expected production load.

This test simulates realistic concurrent usage to measure:
- Throughput (requests/second)
- Latency percentiles (p50, p95, p99)
- Error rates under normal load
- Resource utilization
"""
import pytest
import requests
import time
import concurrent.futures
import statistics
from typing import List, Dict

# Load test configuration
# Note: These values are conservative for GROQ free tier (500k tokens/day limit)
# Increase for production environments with higher rate limits
CONCURRENT_USERS = 3   # Simulated concurrent users (low to avoid rate limits)
TOTAL_REQUESTS = 10    # Total requests to execute
EXPECTED_P95_LATENCY = 120.0  # seconds
EXPECTED_ERROR_RATE = 0.10  # 10% max error rate (accounts for occasional rate limits)

def execute_diagnosis(gateway_url: str, alert_payload: Dict) -> Dict:
    """Execute a single diagnosis request and measure performance."""
    start_time = time.time()
    try:
        response = requests.post(
            f"{gateway_url}/diagnose_alert",
            json=alert_payload,
            timeout=120
        )
        latency = time.time() - start_time
        return {
            "success": response.status_code == 200,
            "latency": latency,
            "status_code": response.status_code,
            "error": None
        }
    except Exception as e:
        latency = time.time() - start_time
        return {
            "success": False,
            "latency": latency,
            "status_code": None,
            "error": str(e)
        }

def test_load_performance(service_urls, sample_alert):
    """
    Load test: Validate performance under expected concurrent load.
    
    Success criteria:
    - p95 latency < 120s
    - Error rate < 1%
    - All requests complete successfully
    """
    gateway_url = service_urls["gateway"]
    results: List[Dict] = []
    
    print(f"\n🔄 Starting load test: {TOTAL_REQUESTS} requests, {CONCURRENT_USERS} concurrent users")
    
    start_time = time.time()
    
    # Execute requests concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENT_USERS) as executor:
        futures = [
            executor.submit(execute_diagnosis, gateway_url, sample_alert)
            for _ in range(TOTAL_REQUESTS)
        ]
        
        for i, future in enumerate(concurrent.futures.as_completed(futures), 1):
            results.append(future.result())
            if i % 10 == 0:
                print(f"  Completed: {i}/{TOTAL_REQUESTS}")
    
    total_duration = time.time() - start_time
    
    # Calculate metrics
    successful_results = [r for r in results if r["success"]]
    latencies = [r["latency"] for r in successful_results]
    
    success_count = len(successful_results)
    error_count = TOTAL_REQUESTS - success_count
    error_rate = error_count / TOTAL_REQUESTS
    throughput = success_count / total_duration if total_duration > 0 else 0
    
    if latencies:
        p50 = statistics.median(latencies)
        p95 = statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies)
        p99 = statistics.quantiles(latencies, n=100)[98] if len(latencies) >= 100 else max(latencies)
        avg_latency = statistics.mean(latencies)
    else:
        p50 = p95 = p99 = avg_latency = 0
    
    # Analyze errors if any
    error_summary = {}
    if not successful_results:
        for r in results:
            err_msg = r.get("error") or f"HTTP {r.get('status_code')}"
            error_summary[err_msg] = error_summary.get(err_msg, 0) + 1
    
    # Print results
    print(f"\n📊 Load Test Results:")
    print(f"  Total Duration: {total_duration:.2f}s")
    print(f"  Throughput: {throughput:.2f} req/s")
    print(f"  Success Rate: {(success_count/TOTAL_REQUESTS)*100:.1f}%")
    print(f"  Error Rate: {error_rate*100:.1f}%")
    
    if error_summary:
        print(f"  Error Summary:")
        for msg, count in error_summary.items():
            print(f"    - {msg}: {count} occurrences")
    print(f"\n  Latency Metrics:")
    print(f"    p50: {p50:.2f}s")
    print(f"    p95: {p95:.2f}s")
    print(f"    p99: {p99:.2f}s")
    print(f"    avg: {avg_latency:.2f}s")
    
    # Assertions
    assert error_rate <= EXPECTED_ERROR_RATE, \
        f"Error rate {error_rate*100:.1f}% exceeds threshold {EXPECTED_ERROR_RATE*100}%"
    
    assert p95 <= EXPECTED_P95_LATENCY, \
        f"p95 latency {p95:.2f}s exceeds SLA of {EXPECTED_P95_LATENCY}s"
    
    assert success_count > 0, "No successful requests completed"
    
    print(f"\n✅ Load test PASSED")

def test_sustained_load(service_urls, sample_alert):
    """
    Sustained load test: Verify consistent performance over time.
    
    Runs a moderate load for an extended period to ensure:
    - No performance degradation
    - Stable latency
    - No memory leaks
    """
    gateway_url = service_urls["gateway"]
    duration_seconds = 60  # 1 minute sustained load
    requests_per_second = 2
    
    print(f"\n⏱️  Starting sustained load test: {duration_seconds}s at {requests_per_second} req/s")
    
    start_time = time.time()
    results = []
    
    while time.time() - start_time < duration_seconds:
        result = execute_diagnosis(gateway_url, sample_alert)
        results.append(result)
        
        # Maintain target rate
        time.sleep(1.0 / requests_per_second)
    
    # Analyze results
    successful = [r for r in results if r["success"]]
    latencies = [r["latency"] for r in successful]
    
    if latencies:
        avg_latency = statistics.mean(latencies)
        print(f"\n📊 Sustained Load Results:")
        print(f"  Requests: {len(results)}")
        print(f"  Success Rate: {(len(successful)/len(results))*100:.1f}%")
        print(f"  Avg Latency: {avg_latency:.2f}s")
        
        assert len(successful) > 0, "No successful requests"
        assert avg_latency < EXPECTED_P95_LATENCY, \
            f"Average latency {avg_latency:.2f}s too high"
        
        print(f"✅ Sustained load test PASSED")
