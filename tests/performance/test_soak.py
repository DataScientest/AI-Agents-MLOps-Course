"""
Soak Testing: Long-running stability test.

This test runs a moderate load for an extended period to detect:
- Memory leaks
- Resource exhaustion over time
- Performance degradation
- Connection pool issues
"""
import pytest
import requests
import time
import concurrent.futures
import statistics
from typing import List, Dict
from collections import defaultdict

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
            "timestamp": time.time()
        }
    except Exception as e:
        latency = time.time() - start_time
        return {
            "success": False,
            "latency": latency,
            "timestamp": time.time(),
            "error": str(e)
        }

@pytest.mark.slow
@pytest.mark.soak
def test_soak_stability(service_urls, sample_alert):
    """
    Soak test: Run moderate load for extended period.
    
    Configuration:
    - Duration: 5 minutes (300 seconds)
    - Concurrency: 3 users
    - Rate: ~1 request per second
    
    Validates:
    - No memory leaks (stable performance over time)
    - No connection exhaustion
    - Consistent latency
    """
    gateway_url = service_urls["gateway"]
    
    # Soak test configuration
    duration_seconds = 300  # 5 minutes
    concurrency = 3
    target_rate = 1.0  # requests per second
    
    print(f"\n🔬 Starting soak test:")
    print(f"  Duration: {duration_seconds}s ({duration_seconds/60:.1f} minutes)")
    print(f"  Concurrency: {concurrency}")
    print(f"  Target Rate: {target_rate} req/s")
    
    start_time = time.time()
    results = []
    
    # Track metrics over time (in 30-second windows)
    window_size = 30
    windows = defaultdict(list)
    
    def worker():
        """Worker function for concurrent execution."""
        while time.time() - start_time < duration_seconds:
            result = execute_diagnosis(gateway_url, sample_alert)
            results.append(result)
            
            # Maintain target rate
            time.sleep(1.0 / target_rate / concurrency)
    
    # Run workers concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(worker) for _ in range(concurrency)]
        concurrent.futures.wait(futures)
    
    total_duration = time.time() - start_time
    
    # Organize results into time windows
    for result in results:
        window_index = int((result["timestamp"] - start_time) / window_size)
        windows[window_index].append(result)
    
    # Analyze each window
    print(f"\n📊 Performance Over Time (30s windows):")
    print(f"  Window | Requests | Success% | Avg Latency | p95 Latency")
    print(f"  " + "-" * 65)
    
    window_metrics = []
    for window_idx in sorted(windows.keys()):
        window_results = windows[window_idx]
        successful = [r for r in window_results if r["success"]]
        latencies = [r["latency"] for r in successful]
        
        success_rate = len(successful) / len(window_results) if window_results else 0
        avg_latency = statistics.mean(latencies) if latencies else 0
        p95_latency = statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else (max(latencies) if latencies else 0)
        
        window_metrics.append({
            "success_rate": success_rate,
            "avg_latency": avg_latency,
            "p95_latency": p95_latency
        })
        
        print(f"  {window_idx:6d} | {len(window_results):8d} | {success_rate*100:7.1f}% | "
              f"{avg_latency:11.2f}s | {p95_latency:11.2f}s")
    
    # Overall statistics
    all_successful = [r for r in results if r["success"]]
    all_latencies = [r["latency"] for r in all_successful]
    
    overall_success_rate = len(all_successful) / len(results) if results else 0
    overall_avg_latency = statistics.mean(all_latencies) if all_latencies else 0
    overall_throughput = len(all_successful) / total_duration if total_duration > 0 else 0
    
    print(f"\n📊 Overall Soak Test Results:")
    print(f"  Total Duration: {total_duration:.2f}s")
    print(f"  Total Requests: {len(results)}")
    print(f"  Success Rate: {overall_success_rate*100:.1f}%")
    print(f"  Throughput: {overall_throughput:.2f} req/s")
    print(f"  Avg Latency: {overall_avg_latency:.2f}s")
    
    # Check for degradation over time
    if len(window_metrics) >= 2:
        first_window_latency = window_metrics[0]["avg_latency"]
        last_window_latency = window_metrics[-1]["avg_latency"]
        degradation = ((last_window_latency - first_window_latency) / first_window_latency * 100) if first_window_latency > 0 else 0
        
        print(f"\n  Performance Degradation:")
        print(f"    First Window Latency: {first_window_latency:.2f}s")
        print(f"    Last Window Latency: {last_window_latency:.2f}s")
        print(f"    Degradation: {degradation:+.1f}%")
        
        # Assert no significant degradation (allow 20% increase)
        assert degradation < 20, \
            f"Performance degraded by {degradation:.1f}% - possible memory leak or resource exhaustion"
    
    # Assert overall stability
    assert overall_success_rate >= 0.95, \
        f"Success rate {overall_success_rate*100:.1f}% below 95% threshold"
    
    assert overall_avg_latency < 120, \
        f"Average latency {overall_avg_latency:.2f}s exceeds 120s threshold"
    
    print(f"\n✅ Soak test PASSED - System is stable over time")

@pytest.mark.slow
@pytest.mark.soak
def test_soak_memory_stability(service_urls):
    """
    Memory stability test: Verify no memory leaks.
    
    Note: This is a simplified version. In production, you would:
    - Monitor actual memory usage via metrics
    - Check for growing heap size
    - Verify garbage collection is working
    """
    print(f"\n💾 Memory stability test")
    print(f"  Note: For full memory leak detection, monitor Prometheus metrics:")
    print(f"  - process_resident_memory_bytes")
    print(f"  - python_gc_objects_uncollectable_total")
    print(f"  - Check metrics at: http://localhost:8005/metrics")
    
    # This test would typically:
    # 1. Record baseline memory usage
    # 2. Run load for extended period
    # 3. Compare final memory usage
    # 4. Assert memory didn't grow significantly
    
    # For now, we just verify metrics endpoint is accessible
    agent_url = service_urls["agent"]
    response = requests.get(f"{agent_url}/metrics")
    assert response.status_code == 200, "Metrics endpoint should be accessible"
    
    # Check for memory-related metrics
    metrics_text = response.text
    assert "process_resident_memory_bytes" in metrics_text, \
        "Memory metrics should be available"
    
    print(f"✅ Memory metrics are being collected - monitor over time for leaks")
