import logging
import time
from typing import Optional
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

class GrafanaDashboardLinkTool:
    def __init__(self, grafana_url: str):
        self.grafana_url = grafana_url

    def get_link(self, dashboard_uid: str, time_range_minutes: int, service_filter: Optional[str] = None) -> str:
        logger.info(f"Generating Grafana link: {dashboard_uid}, range: {time_range_minutes}m")
        try:
            if time_range_minutes <= 0:
                raise ValueError("time_range_minutes must be positive.")
            
            to_time = int(time.time() * 1000)
            from_time = to_time - (time_range_minutes * 60 * 1000)

            base_url = f"{self.grafana_url}/d/{dashboard_uid}" 
            params = {
                "from": from_time,
                "to": to_time,
                "orgId": 1
            }
            if service_filter:
                params["var-service"] = service_filter 
            
            full_url = f"{base_url}?{urlencode(params)}"
            return f"Grafana Dashboard Link: {full_url}"
        except Exception as e:
            logger.error(f"Error generating Grafana link: {e}")
            return f"Error: {e}"
