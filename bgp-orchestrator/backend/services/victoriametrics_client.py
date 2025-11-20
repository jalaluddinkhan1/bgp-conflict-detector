"""
VictoriaMetrics client for long-term time-series storage.

VictoriaMetrics is a fast, cost-effective, and scalable monitoring solution
and time-series database. This client provides integration for storing and
querying metrics with VictoriaMetrics.
"""
import json
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin

import httpx
from app.middleware.logging import logger


class VictoriaMetricsClient:
    """
    Client for VictoriaMetrics API.
    
    Supports:
    - Writing metrics via Prometheus remote write API
    - Querying metrics via PromQL
    - Long-term storage of time-series data
    """

    def __init__(
        self,
        base_url: str,
        remote_write_path: str = "/api/v1/write",
        query_path: str = "/api/v1/query",
        query_range_path: str = "/api/v1/query_range",
        timeout: float = 30.0,
    ):
        """
        Initialize VictoriaMetrics client.
        
        Args:
            base_url: Base URL for VictoriaMetrics (e.g., "http://victoriametrics:8428")
            remote_write_path: Path for remote write API
            query_path: Path for instant queries
            query_range_path: Path for range queries
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.remote_write_url = urljoin(self.base_url, remote_write_path)
        self.query_url = urljoin(self.base_url, query_path)
        self.query_range_url = urljoin(self.base_url, query_range_path)
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)

    async def write_metric(
        self,
        metric_name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
        timestamp_ms: Optional[int] = None,
    ) -> bool:
        """
        Write a single metric to VictoriaMetrics.
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            labels: Optional labels dictionary
            timestamp_ms: Optional timestamp in milliseconds (default: now)
            
        Returns:
            True if successful, False otherwise
        """
        import time
        
        if timestamp_ms is None:
            timestamp_ms = int(time.time() * 1000)
        
        # Build metric line in Prometheus format
        label_str = ""
        if labels:
            label_pairs = [f'{k}="{v}"' for k, v in labels.items()]
            label_str = "{" + ",".join(label_pairs) + "}"
        
        metric_line = f"{metric_name}{label_str} {value} {timestamp_ms}\n"
        
        try:
            response = await self.client.post(
                self.remote_write_url,
                content=metric_line.encode("utf-8"),
                headers={"Content-Type": "application/x-protobuf"},
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to write metric to VictoriaMetrics: {e}")
            return False

    async def write_metrics_batch(self, metrics: List[Tuple[str, float, Optional[Dict[str, str]]]]) -> bool:
        """
        Write multiple metrics in a batch.
        
        Args:
            metrics: List of (metric_name, value, labels) tuples
            
        Returns:
            True if successful, False otherwise
        """
        import time
        
        timestamp_ms = int(time.time() * 1000)
        metric_lines = []
        
        for metric_name, value, labels in metrics:
            label_str = ""
            if labels:
                label_pairs = [f'{k}="{v}"' for k, v in labels.items()]
                label_str = "{" + ",".join(label_pairs) + "}"
            
            metric_line = f"{metric_name}{label_str} {value} {timestamp_ms}\n"
            metric_lines.append(metric_line)
        
        metric_data = "".join(metric_lines)
        
        try:
            response = await self.client.post(
                self.remote_write_url,
                content=metric_data.encode("utf-8"),
                headers={"Content-Type": "application/x-protobuf"},
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to write metrics batch to VictoriaMetrics: {e}")
            return False

    async def query(self, promql: str, time: Optional[int] = None) -> Optional[Dict]:
        """
        Execute a PromQL instant query.
        
        Args:
            promql: PromQL query string
            time: Optional Unix timestamp in seconds (default: now)
            
        Returns:
            Query result dictionary or None on error
        """
        params = {"query": promql}
        if time:
            params["time"] = time
        
        try:
            response = await self.client.get(self.query_url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to query VictoriaMetrics: {e}")
            return None

    async def query_range(
        self,
        promql: str,
        start: int,
        end: int,
        step: str = "15s",
    ) -> Optional[Dict]:
        """
        Execute a PromQL range query.
        
        Args:
            promql: PromQL query string
            start: Start timestamp (Unix seconds)
            end: End timestamp (Unix seconds)
            step: Query resolution step (e.g., "15s", "1m")
            
        Returns:
            Query result dictionary or None on error
        """
        params = {
            "query": promql,
            "start": start,
            "end": end,
            "step": step,
        }
        
        try:
            response = await self.client.get(self.query_range_url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to query range from VictoriaMetrics: {e}")
            return None

    async def health_check(self) -> bool:
        """
        Check if VictoriaMetrics is healthy.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            health_url = urljoin(self.base_url, "/health")
            response = await self.client.get(health_url)
            return response.status_code == 200
        except Exception:
            return False

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


# Global client instance
_vm_client: Optional[VictoriaMetricsClient] = None


def get_victoriametrics_client() -> Optional[VictoriaMetricsClient]:
    """
    Get or create VictoriaMetrics client instance.
    
    Returns:
        VictoriaMetricsClient instance or None if not configured
    """
    global _vm_client
    
    from app.config import settings
    
    # Check if VictoriaMetrics is configured
    vm_url = getattr(settings, "VICTORIAMETRICS_URL", None)
    if not vm_url:
        return None
    
    if _vm_client is None:
        _vm_client = VictoriaMetricsClient(base_url=vm_url)
    
    return _vm_client

