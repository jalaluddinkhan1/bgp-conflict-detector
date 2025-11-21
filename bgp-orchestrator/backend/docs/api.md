# API Reference

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

All endpoints (except health checks) require authentication via JWT token:

```
Authorization: Bearer <token>
```

## Endpoints

### Health Checks

#### GET /health/healthz

Deep health check with dependency verification.

**Response**:
```json
{
  "status": "healthy",
  "checks": {
    "database": {"status": "healthy", "latency_ms": 1.23},
    "redis": {"status": "healthy", "latency_ms": 0.45}
  },
  "version": "1.0.0"
}
```

### Conflict Detection

#### POST /detection/detect

Detect conflicts in BGP peerings.

**Request Body**:
```json
{
  "peerings": [
    {
      "local_asn": 65000,
      "peer_asn": 65001,
      "peer_ip": "192.0.2.1",
      "local_ip": "192.0.2.2"
    }
  ]
}
```

**Response**:
```json
{
  "conflicts": [
    {
      "type": "asn_collision",
      "severity": "high",
      "description": "ASN collision detected",
      "affected_peers": [1, 2],
      "recommended_action": "Resolve ASN collision"
    }
  ]
}
```

### Machine Learning

#### POST /ml/predict

Predict BGP flap probability.

**Request Body**:
```json
{
  "cpu_usage": 75.5,
  "memory_usage": 82.3,
  "interface_errors": 5,
  "hold_time": 180,
  "peer_uptime_seconds": 86400,
  "as_path_length": 4,
  "prefix_count": 50000
}
```

**Response**:
```json
{
  "flap_probability": 0.23,
  "confidence": 0.85,
  "model_version": "1.0.0"
}
```

### Anomaly Detection

#### POST /anomalies/detect

Detect anomalies in time-series data.

**Request Body**:
```json
{
  "metric_name": "bgp_session_flaps",
  "timestamps": ["2024-01-01T00:00:00Z", "2024-01-01T01:00:00Z"],
  "values": [0, 5],
  "device": "router01"
}
```

**Response**:
```json
{
  "anomalies": [
    {
      "timestamp": "2024-01-01T01:00:00Z",
      "value": 5,
      "severity": "high",
      "score": 0.95
    }
  ]
}
```

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error message",
  "status_code": 400
}
```

Common status codes:
- `400`: Bad Request
- `401`: Unauthorized
- `403`: Forbidden
- `404`: Not Found
- `422`: Validation Error
- `429`: Rate Limit Exceeded
- `500`: Internal Server Error

