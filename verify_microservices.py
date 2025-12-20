import requests
import json
import time

def test_health():
    print("\n[1] Checking Health Endpoints...")
    services = {
        "Gateway": "http://localhost:8000/health",
        "Agent Core": "http://localhost:8005/health",
        "Knowledge Base": "http://localhost:8006/health",
        "System Tool": "http://localhost:8004/health",
        "Prometheus Tool": "http://localhost:8001/health",
        "Loki Tool": "http://localhost:8002/health",
        "Grafana Tool": "http://localhost:8003/health"
    }
    
    for name, url in services.items():
        try:
            resp = requests.get(url, timeout=5)
            status = "UP" if resp.status_code == 200 else f"ERROR ({resp.status_code})"
            print(f"  - {name}: {status}")
        except Exception as e:
            print(f"  - {name}: DOWN ({e})")

def test_diagnose():
    print("\n[2] Testing Diagnostic Flow via Gateway...")
    url = "http://localhost:8000/diagnose_alert"
    payload = {
        "alert_info": "High CPU usage on news-classifier-api after recent deployment",
        "service_name": "news-classifier-api",
        "alert_type": "HighCPULoad"
    }
    
    print(f"  Sending request for: {payload['alert_info']}")
    try:
        start_time = time.time()
        resp = requests.post(url, json=payload, timeout=120)
        duration = time.time() - start_time
        
        if resp.status_code == 200:
            result = resp.json()
            print(f"  ✅ Success (took {duration:.2f}s)")
            print("\n--- Diagnostic Summary ---")
            print(result.get("final_result", "No summary found."))
            print("--------------------------")
        else:
            print(f"  ❌ Failed ({resp.status_code}): {resp.text}")
    except Exception as e:
        print(f"  ❌ Error: {e}")

if __name__ == "__main__":
    test_health()
    # Wait a bit for services to be fully ready if needed
    test_diagnose()
