import logging
import requests
import time
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class SystemMetricsTool:
    """Tool to fetch system metrics from Prometheus (node-exporter)."""
    
    def __init__(self, prometheus_url: str):
        self.prometheus_url = prometheus_url
        
    def get_metrics(self, component: str, target_service: Optional[str] = None) -> str:
        """Fetch metrics for a component (CPU, Memory, Disk)."""
        logger.info(f"Fetching {component} metrics for {target_service or 'all nodes'}")
        
        # Mapping component to PromQL queries
        queries = {
            "CPU": '100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)',
            "Memory": '100 * (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes))',
            "Disk": '100 * (1 - (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"}))'
        }
        
        query = queries.get(component)
        if not query:
            return f"Error: Unknown component '{component}'. Available: CPU, Memory, Disk"
            
        try:
            response = requests.get(
                f"{self.prometheus_url}/api/v1/query",
                params={"query": query}
            )
            response.raise_for_status()
            data = response.json()
            
            if data["status"] == "success" and data["data"]["result"]:
                results = []
                for res in data["data"]["result"]:
                    val = float(res["value"][1])
                    results.append(f"{component} usage: {val:.2f}%")
                return "\n".join(results)
            else:
                return f"No {component} metrics found in Prometheus."
                
        except Exception as e:
            logger.error(f"Error querying Prometheus for system metrics: {e}")
            return f"Error fetching system metrics: {e}"
