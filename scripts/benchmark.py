import requests
import time
import concurrent.futures
import statistics
import json
import argparse
import os

def run_diagnosis(gateway_url, alert_payload):
    start_time = time.time()
    try:
        response = requests.post(f"{gateway_url}/diagnose_alert", json=alert_payload, timeout=120)
        latency = time.time() - start_time
        return {
            "status_code": response.status_code,
            "latency": latency,
            "success": response.status_code == 200,
            "error": None if response.status_code == 200 else response.text
        }
    except Exception as e:
        latency = time.time() - start_time
        return {
            "status_code": None,
            "latency": latency,
            "success": False,
            "error": str(e)
        }

def run_benchmark(gateway_url, num_requests, concurrency, alert_payload):
    print(f"Starting benchmark: {num_requests} total requests, {concurrency} concurrent")
    print(f"Target Gateway: {gateway_url}")
    
    results = []
    start_time = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(run_diagnosis, gateway_url, alert_payload) for _ in range(num_requests)]
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())
            if len(results) % 5 == 0:
                print(f"Completed {len(results)}/{num_requests} requests...")
                
    total_duration = time.time() - start_time
    
    # Calculate metrics
    latencies = [r["latency"] for r in results if r["success"]]
    success_count = sum(1 for r in results if r["success"])
    error_count = num_requests - success_count
    
    if latencies:
        p50 = statistics.median(latencies)
        p95 = statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies)
        p99 = statistics.quantiles(latencies, n=100)[98] if len(latencies) >= 100 else max(latencies)
        avg_latency = statistics.mean(latencies)
    else:
        p50 = p95 = p99 = avg_latency = 0
        
    throughput = success_count / total_duration if total_duration > 0 else 0
    
    report = {
        "summary": {
            "total_requests": num_requests,
            "concurrency": concurrency,
            "total_duration_seconds": total_duration,
            "throughput_req_per_sec": throughput,
            "success_rate": (success_count / num_requests) * 100 if num_requests > 0 else 0
        },
        "latency_metrics": {
            "avg": avg_latency,
            "p50": p50,
            "p95": p95,
            "p99": p99,
            "min": min(latencies) if latencies else 0,
            "max": max(latencies) if latencies else 0
        },
        "errors": [r["error"] for r in results if not r["success"]][:10] # Show first 10 errors
    }
    
    return report

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AIOps Agent Performance Benchmark")
    parser.add_argument("--url", default="http://localhost:8000", help="API Gateway URL")
    parser.add_argument("--requests", type=int, default=10, help="Total requests to run")
    parser.add_argument("--concurrency", type=int, default=2, help="Concurrency level")
    parser.add_argument("--output", default="benchmark_report.json", help="Output JSON file")
    
    args = parser.parse_args()
    
    sample_alert = {
        "alerts": [{
            "labels": {
                "alertname": "HighCPUUsage",
                "service": "news-classifier",
                "severity": "critical",
                "instance": "prod-server-01"
            },
            "annotations": {
                "summary": "CPU usage is above 90%",
                "description": "CPU usage is above 90%"
            }
        }]
    }
    
    report = run_benchmark(args.url, args.requests, args.concurrency, sample_alert)
    
    print("\nBenchmark Results:")
    print(f"  Success Rate: {report['summary']['success_rate']:.2f}%")
    print(f"  Throughput: {report['summary']['throughput_req_per_sec']:.2f} req/s")
    print(f"  p50 Latency: {report['latency_metrics']['p50']:.4f}s")
    print(f"  p95 Latency: {report['latency_metrics']['p95']:.4f}s")
    print(f"  p99 Latency: {report['latency_metrics']['p99']:.4f}s")
    
    with open(args.output, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nDetailed report saved to {args.output}")
