"""
Stress Testing: Find the breaking point of the system.

This test gradually increases load beyond normal capacity to:
- Identify bottlenecks
- Find maximum throughput
- Verify graceful degradation
- Test recovery after overload
"""
import pytest
import requests
import time
import concurrent.futures
import statistics
from typing import List, Dict

def execute_diagnosis(gateway_url: str, alert_payload: Dict) -> Dict:
    """Execute a single diagnosis request."""
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
            "status_code": response.status_code
        }
    except Exception as e:
        latency = time.time() - start_time
        return {
            "success": False,
            "latency": latency,
            "status_code": None,
            "error": str(e)
        }

@pytest.mark.slow
def test_stress_increasing_load(service_urls, sample_alert):
    """
    Stress test: Gradually increase load to find breaking point.
    
    Tests with increasing concurrency levels:
    - 5, 10, 15, 20, 25 concurrent users
    - Measures degradation at each level
    - Identifies saturation point
    """
    gateway_url = service_urls["gateway"]
    concurrency_levels = [5, 10, 15, 20]
    requests_per_level = 20
    
    print(f"\n🔥 Starting stress test with increasing load")
    
    results_by_level = {}
    
    for concurrency in concurrency_levels:
        print(f"\n  Testing with {concurrency} concurrent users...")
        
        results = []
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [
                executor.submit(execute_diagnosis, gateway_url, sample_alert)
                for _ in range(requests_per_level)
            ]
            
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())
        
        total_duration = time.time() - start_time
        
        # Calculate metrics
        successful = [r for r in results if r["success"]]
        latencies = [r["latency"] for r in successful]
        
        success_rate = len(successful) / len(results) if results else 0
        throughput = len(successful) / total_duration if total_duration > 0 else 0
        avg_latency = statistics.mean(latencies) if latencies else 0
        p95_latency = statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else (max(latencies) if latencies else 0)
        
        results_by_level[concurrency] = {
            "success_rate": success_rate,
            "throughput": throughput,
            "avg_latency": avg_latency,
            "p95_latency": p95_latency
        }
        
        print(f"    Success Rate: {success_rate*100:.1f}%")
        print(f"    Throughput: {throughput:.2f} req/s")
        print(f"    Avg Latency: {avg_latency:.2f}s")
        print(f"    p95 Latency: {p95_latency:.2f}s")
        
        # Stop if success rate drops significantly
        if success_rate < 0.8:
            print(f"\n⚠️  Breaking point reached at {concurrency} concurrent users")
            break
    
    # Print summary
    print(f"\n📊 Stress Test Summary:")
    for level, metrics in results_by_level.items():
        print(f"  {level} users: {metrics['success_rate']*100:.1f}% success, "
              f"{metrics['throughput']:.2f} req/s, "
              f"p95: {metrics['p95_latency']:.2f}s")
    
    # Verify system handled at least baseline load
    assert results_by_level[5]["success_rate"] >= 0.95, \
        "System should handle 5 concurrent users with >95% success"
    
    print(f"\n✅ Stress test completed")

@pytest.mark.slow
def test_spike_load(service_urls, sample_alert):
    """
    Spike test: Sudden burst of traffic.
    
    Simulates a traffic spike to verify:
    - System handles sudden load increase
    - No cascading failures
    - Recovery after spike
    """
    gateway_url = service_urls["gateway"]
    spike_concurrency = 30
    spike_requests = 30
    
    print(f"\n⚡ Starting spike test: {spike_requests} requests at {spike_concurrency} concurrency")
    
    start_time = time.time()
    results = []
    
    # Execute spike
    with concurrent.futures.ThreadPoolExecutor(max_workers=spike_concurrency) as executor:
        futures = [
            executor.submit(execute_diagnosis, gateway_url, sample_alert)
            for _ in range(spike_requests)
        ]
        
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())
    
    spike_duration = time.time() - start_time
    
    # Analyze spike results
    successful = [r for r in results if r["success"]]
    success_rate = len(successful) / len(results) if results else 0
    
    print(f"\n📊 Spike Test Results:")
    print(f"  Duration: {spike_duration:.2f}s")
    print(f"  Success Rate: {success_rate*100:.1f}%")
    print(f"  Successful: {len(successful)}/{len(results)}")
    
    # Verify system didn't completely fail
    assert success_rate >= 0.5, \
        f"System should handle spike with at least 50% success rate, got {success_rate*100:.1f}%"
    
    # Test recovery - send a few normal requests
    print(f"\n  Testing recovery...")
    time.sleep(5)  # Wait for system to recover
    
    recovery_result = execute_diagnosis(gateway_url, sample_alert)
    assert recovery_result["success"], "System should recover after spike"
    
    print(f"✅ Spike test PASSED - System recovered successfully")
