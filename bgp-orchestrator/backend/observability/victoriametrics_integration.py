"""
VictoriaMetrics integration for Prometheus metrics.

This module provides integration between Prometheus metrics and VictoriaMetrics
for long-term storage. It can be used to forward metrics from Prometheus to
VictoriaMetrics via remote write API.
"""
import asyncio
from typing import Optional

from app.config import settings
from app.middleware.logging import logger
from observability.metrics import registry
from prometheus_client import CollectorRegistry, generate_latest
from services.victoriametrics_client import VictoriaMetricsClient, get_victoriametrics_client


async def forward_metrics_to_victoriametrics() -> bool:
    """
    Forward current Prometheus metrics to VictoriaMetrics.
    
    This function reads all metrics from the Prometheus registry and
    forwards them to VictoriaMetrics using the remote write API.
    
    Returns:
        True if successful, False otherwise
    """
    if not settings.VICTORIAMETRICS_ENABLED:
        return False
    
    vm_client = get_victoriametrics_client()
    if not vm_client:
        logger.warning("VictoriaMetrics client not available")
        return False
    
    try:
        # Check health first
        if not await vm_client.health_check():
            logger.warning("VictoriaMetrics health check failed")
            return False
        
        # Generate Prometheus format metrics
        metrics_text = generate_latest(registry).decode("utf-8")
        
        metrics_to_write = []
        
        for line in metrics_text.split("\n"):
            if not line or line.startswith("#"):
                continue
            
            # Parse Prometheus format: metric_name{labels} value timestamp
            parts = line.split()
            if len(parts) < 2:
                continue
            
            metric_part = parts[0]
            value = float(parts[1])
            
            # Parse metric name and labels
            if "{" in metric_part:
                metric_name, labels_part = metric_part.split("{", 1)
                labels_part = labels_part.rstrip("}")
                labels = {}
                if labels_part:
                    for label_pair in labels_part.split(","):
                        if "=" in label_pair:
                            key, val = label_pair.split("=", 1)
                            labels[key] = val.strip('"')
            else:
                metric_name = metric_part
                labels = None
            
            metrics_to_write.append((metric_name, value, labels))
        
        # Write metrics in batch
        if metrics_to_write:
            success = await vm_client.write_metrics_batch(metrics_to_write)
            if success:
                logger.debug(f"Forwarded {len(metrics_to_write)} metrics to VictoriaMetrics")
            return success
        
        return True
        
    except Exception as e:
        logger.error(f"Error forwarding metrics to VictoriaMetrics: {e}", exc_info=True)
        return False


async def start_victoriametrics_forwarder(interval_seconds: int = 60) -> None:
    """
    Start a background task to periodically forward metrics to VictoriaMetrics.
    
    Args:
        interval_seconds: Interval between forwarding operations (default: 60s)
    """
    if not settings.VICTORIAMETRICS_ENABLED:
        logger.info("VictoriaMetrics forwarding disabled")
        return
    
    logger.info(f"Starting VictoriaMetrics forwarder (interval: {interval_seconds}s)")
    
    while True:
        try:
            await asyncio.sleep(interval_seconds)
            await forward_metrics_to_victoriametrics()
        except asyncio.CancelledError:
            logger.info("VictoriaMetrics forwarder stopped")
            break
        except Exception as e:
            logger.error(f"Error in VictoriaMetrics forwarder: {e}", exc_info=True)


# Background task reference
_forwarder_task: Optional[asyncio.Task] = None


def start_background_forwarder(interval_seconds: int = 60) -> None:
    """
    Start the VictoriaMetrics forwarder as a background task.
    
    Args:
        interval_seconds: Interval between forwarding operations
    """
    global _forwarder_task
    
    if not settings.VICTORIAMETRICS_ENABLED:
        return
    
    if _forwarder_task is None or _forwarder_task.done():
        _forwarder_task = asyncio.create_task(start_victoriametrics_forwarder(interval_seconds))
        logger.info("VictoriaMetrics background forwarder started")


def stop_background_forwarder() -> None:
    """Stop the VictoriaMetrics forwarder background task."""
    global _forwarder_task
    
    if _forwarder_task and not _forwarder_task.done():
        _forwarder_task.cancel()
        logger.info("VictoriaMetrics background forwarder stopped")

