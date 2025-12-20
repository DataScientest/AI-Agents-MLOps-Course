import logging
import requests
import time
import re
from typing import Optional

logger = logging.getLogger(__name__)

class LokiLogSearchTool:
    def __init__(self, loki_url: str):
        self.loki_url = loki_url

    def search(self, query: str, time_range_minutes: int, limit: int, target_service: Optional[str] = None) -> str:
        full_query = self._augment_loki_query(query or "", target_service)
        logger.info(f"Searching Loki: '{full_query}', range: {time_range_minutes}m, limit: {limit}")
        try:
            if time_range_minutes <= 0:
                raise ValueError("time_range_minutes must be positive.")
            
            end_time_ns = int(time.time() * 1e9)
            start_time_ns = int(end_time_ns - (time_range_minutes * 60 * 1e9))
            
            params = {
                "query": full_query,
                "start": str(start_time_ns),
                "end": str(end_time_ns),
                "limit": limit
            }
            
            response = requests.get(f"{self.loki_url}/loki/api/v1/query_range", params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data["status"] == "success" and data["data"]["result"]:
                formatted_logs = []
                for stream in data["data"]["result"]:
                    for entry in stream["values"]:
                        formatted_logs.append(f"{entry[0]} {stream['stream']} {entry[1]}")
                return "Loki log search results:\n" + "\n".join(formatted_logs[:limit])
            else:
                return "Loki log search: No logs found."
        except Exception as e:
            logger.error(f"Error querying Loki: {e}")
            return f"Error: {e}"

    def _augment_loki_query(self, query: str, target_service: Optional[str]) -> str:
        if not target_service:
            return query.strip()
        stripped = (query or "").strip()
        default_selector = f'{{job="docker", service="{target_service}"}}'
        if not stripped: return default_selector
        match = re.match(r'^\{([^}]*)\}(.*)$', stripped)
        if not match: return f"{default_selector} {stripped}"
        labels_part, remainder = match.groups()
        segments = [seg.strip() for seg in re.split(r',(?![^\"]*\")', labels_part) if seg.strip()]
        values = {}
        for segment in segments:
            if '=' not in segment: continue
            k, v = segment.split('=', 1)
            values[k.strip()] = v.strip()
        if 'service' not in values: values['service'] = f'"{target_service}"'
        if 'job' not in values: values['job'] = '"docker"'
        rebuilt_labels = ', '.join(f"{k}={v}" for k, v in values.items())
        return f'{{{rebuilt_labels}}}{remainder}'
