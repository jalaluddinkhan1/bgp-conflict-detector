# Architecture

## System Overview

The BGP Conflict Detector is a production-grade system for detecting and managing BGP network conflicts. It provides real-time conflict detection, ML-based anomaly detection, and comprehensive monitoring capabilities.

## Core Components

### 1. Conflict Detection Engine

- **Location**: `core/detector.py`
- **Purpose**: Rule-based conflict detection using pluggable rules
- **Features**:
  - ASN collision detection
  - RPKI validation
  - Session overlap detection
  - Routing loop detection
  - Configuration mismatch detection

### 2. Data Sources

- **Location**: `data/`
- **Supported Sources**:
  - BGPStream (real-time BGP updates)
  - BMP (BGP Monitoring Protocol)
  - RIPE RIS
  - Custom data sources

### 3. Machine Learning Pipeline

- **Location**: `ml/`
- **Components**:
  - Feature engineering
  - Anomaly detection models
  - BGP flap prediction
  - Model training and inference

### 4. Storage

- **Time-Series**: InfluxDB for metrics and BGP updates
- **Cache/State**: Redis for session state and caching
- **Metadata**: PostgreSQL for configuration and conflicts

### 5. API Layer

- **Framework**: FastAPI
- **Endpoints**:
  - Conflict detection
  - Health checks
  - Metrics (Prometheus)
  - ML predictions

### 6. Alerting

- **Channels**: Slack, Grafana OnCall, Email
- **Templates**: Customizable alert templates
- **Routing**: Configurable alert routing

## Data Flow

```
BGP Updates → Data Sources → Conflict Detection → Storage → API → Alerts
                     ↓
              Feature Store → ML Models → Anomaly Detection
```

## Scalability

- Horizontal scaling via Kubernetes
- Stateless API design
- Redis-based session management
- Event-driven architecture with Kafka

## Security

- JWT-based authentication
- OAuth2 integration
- Encrypted data storage
- Role-based access control

