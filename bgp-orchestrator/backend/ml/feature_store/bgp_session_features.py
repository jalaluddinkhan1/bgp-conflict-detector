"""
Feast Feature Definitions for BGP Session Features

Defines features for BGP sessions including:
- Session metrics (uptime, state changes)
- Network metrics (prefix count, AS path length)
- Device metrics (CPU, memory, interface errors)
"""
from datetime import timedelta
from feast import Entity, Feature, FeatureView, ValueType
from feast.data_source import FileSource

# Entity: BGP Session
bgp_session_entity = Entity(
    name="bgp_session",
    value_type=ValueType.STRING,
    description="BGP session identifier (peer_ip:peer_asn)",
)

# Entity: Device
device_entity = Entity(
    name="device",
    value_type=ValueType.STRING,
    description="Network device/router identifier",
)

# Entity: Network Event
network_event_entity = Entity(
    name="network_event",
    value_type=ValueType.STRING,
    description="Network event identifier",
)

# Data Source: BGP Session Features (Parquet files)
bgp_session_features_source = FileSource(
    name="bgp_session_features_source",
    path="s3://bgp-features/bgp_session_features.parquet",  # MinIO S3 path
    timestamp_field="event_timestamp",
    created_timestamp_column="created_timestamp",
)

# Feature View: BGP Session Features
bgp_session_features = FeatureView(
    name="bgp_session_features",
    entities=[bgp_session_entity],
    ttl=timedelta(days=90),  # Keep features for 90 days
    features=[
        Feature(name="peer_uptime_seconds", dtype=ValueType.INT64),
        Feature(name="hold_time", dtype=ValueType.INT64),
        Feature(name="keepalive", dtype=ValueType.INT64),
        Feature(name="prefix_count", dtype=ValueType.INT64),
        Feature(name="as_path_length", dtype=ValueType.INT64),
        Feature(name="session_state", dtype=ValueType.STRING),
        Feature(name="flap_count_24h", dtype=ValueType.INT64),
        Feature(name="last_flap_timestamp", dtype=ValueType.UNIX_TIMESTAMP),
        Feature(name="received_updates_24h", dtype=ValueType.INT64),
        Feature(name="sent_updates_24h", dtype=ValueType.INT64),
    ],
    online=True,  # Enable online serving
    source=bgp_session_features_source,
    tags={"team": "network-ops", "domain": "bgp"},
)

# Data Source: Device Metrics
device_metrics_source = FileSource(
    name="device_metrics_source",
    path="s3://bgp-features/device_metrics.parquet",
    timestamp_field="event_timestamp",
    created_timestamp_column="created_timestamp",
)

# Feature View: Device Metrics
device_metrics = FeatureView(
    name="device_metrics",
    entities=[device_entity],
    ttl=timedelta(days=30),
    features=[
        Feature(name="cpu_usage_percent", dtype=ValueType.FLOAT),
        Feature(name="memory_usage_percent", dtype=ValueType.FLOAT),
        Feature(name="interface_errors", dtype=ValueType.INT64),
        Feature(name="cpu_temperature", dtype=ValueType.FLOAT),
        Feature(name="interface_utilization", dtype=ValueType.FLOAT),
        Feature(name="bgp_sessions_active", dtype=ValueType.INT64),
        Feature(name="bgp_sessions_total", dtype=ValueType.INT64),
    ],
    online=True,
    source=device_metrics_source,
    tags={"team": "network-ops", "domain": "infrastructure"},
)

# Data Source: Network Events
network_events_source = FileSource(
    name="network_events_source",
    path="s3://bgp-features/network_events.parquet",
    timestamp_field="event_timestamp",
    created_timestamp_column="created_timestamp",
)

# Feature View: Network Events
network_events = FeatureView(
    name="network_events",
    entities=[network_event_entity],
    ttl=timedelta(days=7),
    features=[
        Feature(name="event_type", dtype=ValueType.STRING),
        Feature(name="prefix", dtype=ValueType.STRING),
        Feature(name="as_path", dtype=ValueType.STRING),
        Feature(name="announce_count_1h", dtype=ValueType.INT64),
        Feature(name="withdraw_count_1h", dtype=ValueType.INT64),
        Feature(name="conflict_detected", dtype=ValueType.BOOL),
        Feature(name="conflict_severity", dtype=ValueType.STRING),
    ],
    online=True,
    source=network_events_source,
    tags={"team": "network-ops", "domain": "bgp"},
)

