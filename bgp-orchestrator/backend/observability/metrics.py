"""
Prometheus metrics for BGP Orchestrator.
"""
from enum import Enum
from time import time
from typing import Any

from fastapi import APIRouter, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    CollectorRegistry,
    REGISTRY,
)

# Create custom registry for cleaner metrics
registry = CollectorRegistry()


# BGP Peering Metrics
bgp_peerings_total = Counter(
    "bgp_peerings_total",
    "Total number of BGP peerings created",
    ["status"],
    registry=registry,
)

active_peerings = Gauge(
    "bgp_active_peerings",
    "Number of active BGP peerings",
    ["device"],
    registry=registry,
)

peerings_by_device = Gauge(
    "bgp_peerings_by_device",
    "Number of BGP peerings per device",
    ["device"],
    registry=registry,
)

peerings_by_asn = Gauge(
    "bgp_peerings_by_peer_asn",
    "Number of BGP peerings per peer ASN",
    ["peer_asn"],
    registry=registry,
)


# Conflict Detection Metrics
conflicts_detected = Counter(
    "bgp_conflicts_detected_total",
    "Total number of conflicts detected",
    ["type", "severity"],
    registry=registry,
)

conflict_detection_duration = Histogram(
    "bgp_conflict_detection_duration_seconds",
    "Time spent detecting conflicts",
    ["rule_name"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
    registry=registry,
)


# API Metrics
api_requests_total = Counter(
    "api_requests_total",
    "Total number of API requests",
    ["method", "endpoint", "status_code"],
    registry=registry,
)

api_latency = Histogram(
    "api_latency_seconds",
    "API request latency",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=registry,
)

api_errors_total = Counter(
    "api_errors_total",
    "Total number of API errors",
    ["method", "endpoint", "error_type"],
    registry=registry,
)


# Vendor Integration Metrics
vendor_api_calls = Counter(
    "vendor_api_calls_total",
    "Total number of vendor API calls",
    ["vendor", "method", "status"],
    registry=registry,
)

vendor_api_health = Gauge(
    "bgp_orchestrator_vendor_api_healthy",
    "Vendor API health status (1=healthy, 0=unhealthy)",
    ["vendor", "endpoint"],
    registry=registry,
)

# RPKI Validation Metrics
rpki_validation_failures = Counter(
    "bgp_orchestrator_rpki_failures_total",
    "RPKI validation failures",
    ["prefix", "origin_asn"],
    registry=registry,
)

# Conflict Detection Metrics (enhanced)
conflict_detection_latency = Histogram(
    "bgp_orchestrator_conflict_detection_duration_seconds",
    "Time to detect conflicts",
    ["rule_type"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
    registry=registry,
)

vendor_api_latency = Histogram(
    "vendor_api_latency_seconds",
    "Vendor API call latency",
    ["vendor", "method"],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
    registry=registry,
)

vendor_connection_errors = Counter(
    "vendor_connection_errors_total",
    "Total vendor connection errors",
    ["vendor", "error_type"],
    registry=registry,
)


# RIPE RIS Metrics
ripe_ris_latency = Histogram(
    "ripe_ris_latency_seconds",
    "RIPE RIS API call latency",
    ["operation"],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
    registry=registry,
)

ripe_ris_events_processed = Counter(
    "ripe_ris_events_processed_total",
    "Total RIPE RIS events processed",
    ["event_type"],
    registry=registry,
)

ripe_ris_cache_hits = Counter(
    "ripe_ris_cache_hits_total",
    "Total RIPE RIS cache hits",
    registry=registry,
)

ripe_ris_cache_misses = Counter(
    "ripe_ris_cache_misses_total",
    "Total RIPE RIS cache misses",
    registry=registry,
)


# Batfish Metrics
batfish_validation_time = Histogram(
    "batfish_validation_duration_seconds",
    "Batfish validation duration",
    ["validation_type"],
    buckets=[0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0],
    registry=registry,
)

batfish_validations_total = Counter(
    "batfish_validations_total",
    "Total number of Batfish validations",
    ["validation_type", "result"],
    registry=registry,
)


# Database Metrics
db_connections_active = Gauge(
    "db_connections_active",
    "Number of active database connections",
    registry=registry,
)

db_queries_total = Counter(
    "db_queries_total",
    "Total number of database queries",
    ["operation", "status"],
    registry=registry,
)

db_query_duration = Histogram(
    "db_query_duration_seconds",
    "Database query duration",
    ["operation"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
    registry=registry,
)


# Redis Metrics
redis_operations_total = Counter(
    "redis_operations_total",
    "Total number of Redis operations",
    ["operation", "status"],
    registry=registry,
)

redis_latency = Histogram(
    "redis_latency_seconds",
    "Redis operation latency",
    ["operation"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0],
    registry=registry,
)

redis_connections_active = Gauge(
    "redis_connections_active",
    "Number of active Redis connections",
    registry=registry,
)


# Audit Metrics
audit_events_total = Counter(
    "audit_events_total",
    "Total number of audit events",
    ["action", "table_name"],
    registry=registry,
)

audit_log_verifications_total = Counter(
    "audit_log_verifications_total",
    "Total number of audit log verifications",
    ["result"],
    registry=registry,
)


# Authentication Metrics
auth_attempts_total = Counter(
    "auth_attempts_total",
    "Total authentication attempts",
    ["provider", "result"],
    registry=registry,
)

auth_token_refreshes_total = Counter(
    "auth_token_refreshes_total",
    "Total token refreshes",
    ["provider"],
    registry=registry,
)


# Rate Limiting Metrics
rate_limit_exceeded_total = Counter(
    "rate_limit_exceeded_total",
    "Total rate limit violations",
    ["endpoint"],
    registry=registry,
)


# Application Metrics
application_uptime = Gauge(
    "application_uptime_seconds",
    "Application uptime in seconds",
    registry=registry,
)

application_version = Gauge(
    "application_version_info",
    "Application version information",
    ["version"],
    registry=registry,
)


# Metrics router
metrics_router = APIRouter(prefix="/metrics", tags=["Metrics"])


@metrics_router.get("", include_in_schema=False)
async def metrics() -> Response:
    """
    Prometheus metrics endpoint.

    Returns:
        Prometheus-formatted metrics
    """
    return Response(
        content=generate_latest(registry),
        media_type=CONTENT_TYPE_LATEST,
    )


# Helper functions for metrics tracking
def track_api_request(method: str, endpoint: str, status_code: int, duration: float) -> None:
    """Track API request metrics."""
    api_requests_total.labels(method=method, endpoint=endpoint, status_code=status_code).inc()
    api_latency.labels(method=method, endpoint=endpoint).observe(duration)


def track_conflict(type: str, severity: str, duration: float, rule_name: str) -> None:
    """Track conflict detection metrics."""
    conflicts_detected.labels(type=type, severity=severity).inc()
    conflict_detection_duration.labels(rule_name=rule_name).observe(duration)


def track_vendor_call(vendor: str, method: str, status: str, duration: float) -> None:
    """Track vendor API call metrics."""
    vendor_api_calls.labels(vendor=vendor, method=method, status=status).inc()
    vendor_api_latency.labels(vendor=vendor, method=method).observe(duration)


def track_ripe_ris_call(operation: str, duration: float, cache_hit: bool = False) -> None:
    """Track RIPE RIS API call metrics."""
    ripe_ris_latency.labels(operation=operation).observe(duration)
    if cache_hit:
        ripe_ris_cache_hits.inc()
    else:
        ripe_ris_cache_misses.inc()


def track_batfish_validation(validation_type: str, duration: float, result: str) -> None:
    """Track Batfish validation metrics."""
    batfish_validation_time.labels(validation_type=validation_type).observe(duration)
    batfish_validations_total.labels(validation_type=validation_type, result=result).inc()


def track_db_query(operation: str, status: str, duration: float) -> None:
    """Track database query metrics."""
    db_queries_total.labels(operation=operation, status=status).inc()
    db_query_duration.labels(operation=operation).observe(duration)


def track_redis_operation(operation: str, status: str, duration: float) -> None:
    """Track Redis operation metrics."""
    redis_operations_total.labels(operation=operation, status=status).inc()
    redis_latency.labels(operation=operation).observe(duration)


def track_audit_event(action: str, table_name: str) -> None:
    """Track audit event metrics."""
    audit_events_total.labels(action=action, table_name=table_name).inc()


def track_auth_attempt(provider: str, result: str) -> None:
    """Track authentication attempt metrics."""
    auth_attempts_total.labels(provider=provider, result=result).inc()


def set_active_peerings_count(device: str, count: int) -> None:
    """Set active peerings count for a device."""
    active_peerings.labels(device=device).set(count)


def set_peerings_by_device(device: str, count: int) -> None:
    """Set peerings count for a device."""
    peerings_by_device.labels(device=device).set(count)


def set_peerings_by_asn(peer_asn: str, count: int) -> None:
    """Set peerings count for a peer ASN."""
    peerings_by_asn.labels(peer_asn=peer_asn).set(count)


def increment_peering_total(status: str) -> None:
    """Increment total peerings counter."""
    bgp_peerings_total.labels(status=status).inc()


def set_db_connections_active(count: int) -> None:
    """Set active database connections count."""
    db_connections_active.set(count)


def set_redis_connections_active(count: int) -> None:
    """Set active Redis connections count."""
    redis_connections_active.set(count)


# Anomaly Detection Metrics
anomaly_detected = Counter(
    "anomaly_detected_total",
    "Total number of anomalies detected",
    ["metric_name", "severity", "anomaly_type"],
    registry=registry,
)

anomaly_detection_duration = Histogram(
    "anomaly_detection_duration_seconds",
    "Time spent detecting anomalies",
    ["metric_name"],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
    registry=registry,
)

anomalies_by_severity = Gauge(
    "anomalies_by_severity",
    "Current number of anomalies by severity",
    ["severity"],
    registry=registry,
)


def track_anomaly(metric_name: str, severity: str, anomaly_type: str, duration: float) -> None:
    """Track anomaly detection metrics."""
    anomaly_detected.labels(
        metric_name=metric_name,
        severity=severity,
        anomaly_type=anomaly_type,
    ).inc()
    anomaly_detection_duration.labels(metric_name=metric_name).observe(duration)


def set_anomalies_by_severity(severity: str, count: int) -> None:
    """Set anomalies count by severity."""
    anomalies_by_severity.labels(severity=severity).set(count)
