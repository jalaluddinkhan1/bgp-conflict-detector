# Phase 1: ML/AI Implementation Summary

This document summarizes the ML/AI features implemented for the BGP Orchestrator.

## 1. BGP Flap Prediction

### Implementation
- **Location**: `backend/ml/bgp_flap_predictor.py`
- **Model**: XGBoost Classifier
- **Features**:
  - `cpu_usage`: CPU utilization percentage (0-100)
  - `memory_usage`: Memory utilization percentage (0-100)
  - `interface_errors`: Number of interface errors
  - `hold_time`: BGP hold time in seconds
  - `peer_uptime_seconds`: Peer uptime in seconds
  - `as_path_length`: AS path length
  - `prefix_count`: Number of prefixes received

### Features
- Synthetic data generation for training
- Model versioning (loads from `./models/`)
- ONNX export for fast inference
- Feature scaling with StandardScaler
- Model persistence (pickle format)

### API Endpoints
- `POST /api/v1/ml/predict` - Predict BGP flap probability
- `GET /api/v1/ml/model/info` - Get model information
- `POST /api/v1/ml/model/train` - Train/retrain model

### Metrics
- `ml_prediction_latency_seconds` - Prometheus histogram for prediction latency

## 2. Anomaly Detection

### Implementation
- **Location**: `backend/observability/anomaly_detector.py`
- **Method**: Prophet (seasonality detection) + 3-sigma rule
- **Supported Metrics**:
  - `bgp_session_flaps`: BGP session flap counts
  - `cpu_temp`: CPU temperature readings
  - `interface_errors`: Interface error counts

### Features
- Prophet-based seasonality detection (daily, weekly)
- 3-sigma anomaly detection
- Severity classification (low, medium, high, critical)
- PostgreSQL storage for anomalies
- Synthetic data generation for testing

### API Endpoints
- `POST /api/v1/anomalies/detect` - Detect anomalies in time-series data
- `GET /api/v1/anomalies/` - List recent anomalies (with filters)
- `GET /api/v1/anomalies/{anomaly_id}` - Get specific anomaly

### Database Model
- **Location**: `backend/models/anomaly.py`
- **Table**: `anomalies`
- **Fields**: metric_name, anomaly_type, timestamp, value, expected_value, deviation, severity, device, metadata

### Metrics
- `anomaly_detected_total` - Counter for detected anomalies
- `anomaly_detection_duration_seconds` - Histogram for detection latency
- `anomalies_by_severity` - Gauge for current anomalies by severity

## 3. Grafana Dashboard

### Location
- `grafana/dashboards/anomaly-detection.json`

### Panels
1. BGP Session Flaps - Anomalies (time series)
2. CPU Temperature - Anomalies (time series)
3. Interface Errors - Anomalies (time series)
4. Anomaly Severity Distribution (bar gauge)
5. Anomalies by Metric Type (pie chart)
6. Anomaly Detection Rate (stat)
7. Total Anomalies (24h) (stat)
8. Anomaly Detection Latency (time series)

## Dependencies Added

```
# Machine Learning & AI
xgboost==2.0.3
scikit-learn==1.3.2
prophet==1.1.5
pandas==2.1.4
numpy==1.26.2

# ONNX Runtime
onnx==1.15.0
onnxruntime==1.16.3
skl2onnx==1.15.0

# Time Series Analysis
statsmodels==0.14.0
```

## Notes

### VictoriaMetrics Integration
VictoriaMetrics support is mentioned in the requirements but requires additional infrastructure setup. The current implementation works with Prometheus. VictoriaMetrics can be added as a drop-in replacement for long-term storage by:
1. Configuring VictoriaMetrics as a remote write target for Prometheus
2. Updating queries to use VictoriaMetrics API if needed

### Model Training
- Models are automatically trained with synthetic data on first use if no model exists
- Models are saved to `./models/` directory
- Model versioning is supported (currently v1.0.0)

### Database Migration
The `anomalies` table needs to be created via Alembic migration:
```bash
alembic revision --autogenerate -m "Add anomalies table"
alembic upgrade head
```

## Usage Examples

### BGP Flap Prediction
```python
POST /api/v1/ml/predict
{
  "cpu_usage": 75.5,
  "memory_usage": 82.3,
  "interface_errors": 5,
  "hold_time": 180,
  "peer_uptime_seconds": 86400,
  "as_path_length": 4,
  "prefix_count": 50000,
  "use_onnx": false
}
```

### Anomaly Detection
```python
POST /api/v1/anomalies/detect
{
  "metric_name": "bgp_session_flaps",
  "timestamps": ["2024-01-01T00:00:00Z", ...],
  "values": [0, 1, 0, 5, 0, ...],
  "device": "router01"
}
```

## Next Steps

1. **Database Migration**: Create Alembic migration for `anomalies` table
2. **VictoriaMetrics**: Set up VictoriaMetrics for long-term metric storage (optional)
3. **Model Training**: Collect real-world data to retrain models
4. **Alerting**: Integrate anomaly detection with alerting system
5. **Dashboard Import**: Import Grafana dashboard JSON into Grafana instance

