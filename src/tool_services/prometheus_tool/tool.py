import logging
import requests
import time
from typing import Optional

logger = logging.getLogger(__name__)

class PrometheusQueryTool:
    def __init__(self, prometheus_url: str):
        self.prometheus_url = prometheus_url

    def query_range(self, query: str, time_range_minutes: int, step_seconds: int, target_service: Optional[str] = None) -> str:
        logger.info(f"Executing PromQL query: '{query}', range: {time_range_minutes}m")
        try:
            if time_range_minutes <= 0:
                raise ValueError("time_range_minutes must be positive.")
            if step_seconds <= 0:
                raise ValueError("step_seconds must be positive.")

            end_time = int(time.time())
            start_time = end_time - (time_range_minutes * 60)

            params = {
                "query": query,
                "start": start_time,
                "end": end_time,
                "step": f"{step_seconds}s"
            }

            response = requests.get(f"{self.prometheus_url}/api/v1/query_range", params=params, timeout=10)
            response.raise_for_status() 
            
            data = response.json()
            
            if data["status"] == "success" and data["data"]["result"]:
                formatted_results = []
                for result in data["data"]["result"]:
                    metric_labels = ', '.join([f"{k}='{v}'" for k, v in result["metric"].items()])
                    values = [f"{float(v[1]):.2f}" for v in result["values"]]
                    formatted_results.append(f"{{ {metric_labels} }} values: {', '.join(values)}")
                
                return "Prometheus query results:\n" + "\n".join(formatted_results)
            else:
                return "Prometheus query: No data found for the given query and time range."
        
        except Exception as e:
            logger.error(f"Error querying Prometheus: {e}")
            return f"Error: {e}"
