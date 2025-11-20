# Streaming Data Pipeline Documentation

This document describes the streaming data pipeline for BGP updates using Kafka and Feast feature store.

## Architecture

```
RIPE RIS / BGP Updates
         ↓
    Kafka Topics
         ↓
  BGP Consumer (aiokafka)
         ↓
    ┌────┴────┐
    ↓         ↓
Conflict    Feature
Detection   Store
    ↓         ↓
PostgreSQL  Redis (Online)
            MinIO (Offline)
```

## Components

### 1. Kafka Consumer (`streaming/bgp_consumer.py`)

**Features:**
- Async Kafka consumer using `aiokafka`
- Real-time conflict detection (<100ms latency)
- Stores updates to PostgreSQL
- Sends features to feature store
- Handles message deserialization

**Configuration:**
```python
KAFKA_ENABLED=true
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
KAFKA_TOPICS=ripe-ris-updates,bgp-updates
KAFKA_GROUP_ID=bgp-orchestrator-consumer
```

### 2. Feature Store (`ml/feature_store/`)

**Components:**
- `feature_store.yaml`: Feast configuration
- `bgp_session_features.py`: Feature definitions
- `feature_store_client.py`: Client for reading/writing features

**Feature Views:**
1. **bgp_session_features**: BGP session metrics
   - peer_uptime_seconds
   - hold_time, keepalive
   - prefix_count, as_path_length
   - session_state, flap_count_24h

2. **device_metrics**: Device/router metrics
   - cpu_usage_percent, memory_usage_percent
   - interface_errors, cpu_temperature
   - bgp_sessions_active

3. **network_events**: Network event features
   - event_type, prefix, as_path
   - announce_count_1h, withdraw_count_1h
   - conflict_detected, conflict_severity

**Stores:**
- **Online Store**: Redis (for real-time serving)
- **Offline Store**: MinIO + Parquet (for batch processing)

### 3. Materialization Job (`streaming/materialization_job.py`)

**Purpose:**
- Materializes features from offline store to online store
- Runs every 5 minutes automatically
- Keeps online store up-to-date for ML inference

## Setup

### 1. Start Kafka Infrastructure

```bash
# Start Kafka, Zookeeper, Schema Registry, Kafka UI
docker-compose -f docker-compose.kafka.yml up -d

# Create topics (optional, auto-created)
docker-compose -f docker-compose.kafka.yml --profile init up kafka-init
```

### 2. Configure Kafka

Add to `.env`:
```bash
KAFKA_ENABLED=true
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPICS=ripe-ris-updates,bgp-updates
KAFKA_GROUP_ID=bgp-orchestrator-consumer
```

### 3. Initialize Feast Feature Store

```bash
cd ml/feature_store

# Initialize Feast repository
feast init

# Apply feature definitions
feast apply

# Materialize features
feast materialize-incremental $(date -u +"%Y-%m-%dT%H:%M:%S")
```

### 4. Configure Feature Store

Add to `.env`:
```bash
FEATURE_STORE_ENABLED=true
FEATURE_STORE_REPO_PATH=./ml/feature_store
```

## Usage

### Consuming BGP Updates

The Kafka consumer starts automatically when `KAFKA_ENABLED=true`:

```python
# Consumer runs in background
# Processes messages from Kafka topics
# Detects conflicts in real-time
# Stores to PostgreSQL and feature store
```

### Serving Features for ML

```bash
# Get features for ML model inference
curl -X POST http://localhost:8000/api/v1/features/serve \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "entity_ids": ["192.168.1.1:65000", "192.168.1.2:65001"],
    "feature_names": ["peer_uptime_seconds", "prefix_count", "as_path_length"]
  }'
```

### Triggering Materialization

```bash
# Manual materialization
curl -X POST "http://localhost:8000/api/v1/features/materialize?start_date=2024-01-01T00:00:00Z&end_date=2024-01-01T23:59:59Z" \
  -H "Authorization: Bearer TOKEN"
```

## Performance

### Targets

- **Latency**: <100ms for conflict detection
- **Throughput**: 1000+ updates/second
- **Materialization**: Every 5 minutes
- **Feature Serving**: <10ms p99 latency

### Monitoring

- Kafka consumer lag
- Processing latency
- Feature store serving latency
- Materialization job status

## Troubleshooting

### Kafka Consumer Not Starting

1. Check Kafka is running:
   ```bash
   docker-compose -f docker-compose.kafka.yml ps
   ```

2. Check configuration:
   ```bash
   echo $KAFKA_BOOTSTRAP_SERVERS
   echo $KAFKA_TOPICS
   ```

3. Check logs:
   ```bash
   kubectl logs deployment/bgp-orchestrator | grep kafka
   ```

### Feature Store Not Working

1. Check Feast is installed:
   ```bash
   pip install feast[redis]
   ```

2. Check feature store path:
   ```bash
   ls -la ml/feature_store/
   ```

3. Verify Redis connection:
   ```bash
   redis-cli ping
   ```

### High Latency

1. Check Kafka consumer lag
2. Optimize conflict detection queries
3. Increase database connection pool
4. Use feature store caching

## Related Documentation

- [Kafka Documentation](https://kafka.apache.org/documentation/)
- [Feast Documentation](https://docs.feast.dev/)
- [RIPE RIS Documentation](https://ris-live.ripe.net/)

