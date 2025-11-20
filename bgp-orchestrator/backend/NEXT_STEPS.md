# Next Steps - Implementation Guide

This document provides step-by-step instructions for completing the setup of the ML/AI features.

## 1. Database Migration

### Run the Alembic Migration

The migration for the `anomalies` table has been created. To apply it:

```bash
cd bgp-orchestrator/backend

# Option 1: Using the migration script
python scripts/run_migrations.py upgrade

# Option 2: Using Alembic directly
alembic upgrade head

# Option 3: Check current migration status
alembic current

# Option 4: View migration history
alembic history
```

### Verify Migration

After running the migration, verify the table was created:

```sql
-- Connect to your PostgreSQL database
psql -U your_user -d bgp_orchestrator

-- Check if table exists
\dt anomalies

-- Check table structure
\d anomalies

-- Check if enums were created
\dT+ anomaly_type
\dT+ anomaly_severity
```

## 2. VictoriaMetrics Setup (Optional)

VictoriaMetrics is configured but disabled by default. To enable it:

### Step 1: Add to Environment Variables

Add to your `.env` file or environment:

```bash
VICTORIAMETRICS_ENABLED=true
VICTORIAMETRICS_URL=http://victoriametrics:8428
```

### Step 2: Deploy VictoriaMetrics

Add to your `docker-compose.yml`:

```yaml
services:
  victoriametrics:
    image: victoriametrics/victoria-metrics:latest
    ports:
      - "8428:8428"
    command:
      - "--storageDataPath=/victoria-metrics-data"
      - "--httpListenAddr=:8428"
    volumes:
      - victoriametrics-data:/victoria-metrics-data
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:8428/health"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  victoriametrics-data:
```

### Step 3: Configure Prometheus Remote Write (Alternative)

Alternatively, configure Prometheus to remote write to VictoriaMetrics:

```yaml
# prometheus.yml
remote_write:
  - url: http://victoriametrics:8428/api/v1/write
```

### Step 4: Verify Integration

The application will automatically start forwarding metrics to VictoriaMetrics if enabled.
Check logs for:

```
VictoriaMetrics forwarder started
Forwarded X metrics to VictoriaMetrics
```

## 3. Model Training

### Automatic Training

Models are automatically trained with synthetic data on first use. When you make the first prediction request:

1. The system detects no model exists
2. Generates 10,000 synthetic training samples
3. Trains the XGBoost model
4. Saves the model to `./models/`
5. Exports to ONNX format

### Manual Training

To manually train or retrain the model:

```bash
# Using the API
curl -X POST http://localhost:8000/api/v1/ml/model/train \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"n_samples": 20000}'

# Or use Python
python -c "
from ml.bgp_flap_predictor import BGPFlapPredictor
predictor = BGPFlapPredictor()
predictor.train(use_synthetic=True, n_samples=20000)
print('Model trained successfully')
"
```

### Training with Real Data

To train with real data, collect your metrics and format them:

```python
import numpy as np
from ml.bgp_flap_predictor import BGPFlapPredictor

# Prepare your data
X = np.array([
    [cpu_usage, memory_usage, interface_errors, hold_time, 
     peer_uptime_seconds, as_path_length, prefix_count],
    # ... more samples
])
y = np.array([0, 1, 0, ...])  # 0 = no flap, 1 = flap

# Train
predictor = BGPFlapPredictor()
metrics = predictor.train(X=X, y=y, use_synthetic=False)
print(f"Training metrics: {metrics}")
```

## 4. Testing the Implementation

### Test BGP Flap Prediction

```bash
curl -X POST http://localhost:8000/api/v1/ml/predict \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "cpu_usage": 75.5,
    "memory_usage": 82.3,
    "interface_errors": 5,
    "hold_time": 180,
    "peer_uptime_seconds": 86400,
    "as_path_length": 4,
    "prefix_count": 50000
  }'
```

### Test Anomaly Detection

```bash
curl -X POST http://localhost:8000/api/v1/anomalies/detect \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "metric_name": "bgp_session_flaps",
    "timestamps": ["2024-01-01T00:00:00Z", "2024-01-01T01:00:00Z"],
    "values": [0, 5],
    "device": "router01"
  }'
```

### Test Model Info

```bash
curl http://localhost:8000/api/v1/ml/model/info \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 5. Grafana Dashboard Import

### Import the Dashboard

1. Open Grafana (typically http://localhost:3000)
2. Go to Dashboards → Import
3. Upload `grafana/dashboards/anomaly-detection.json`
4. Select your Prometheus data source
5. Click "Import"

### Configure Data Source

Ensure your Prometheus data source is configured:
- URL: `http://prometheus:9090` (or your Prometheus URL)
- Access: Server (default)

## 6. Monitoring and Alerts

### Check Prometheus Metrics

Visit `http://localhost:9090/metrics` to see:
- `ml_prediction_latency_seconds` - ML prediction latency
- `anomaly_detected_total` - Total anomalies detected
- `anomaly_detection_duration_seconds` - Anomaly detection latency

### Set Up Alerts (Optional)

Example Prometheus alert rules:

```yaml
groups:
  - name: ml_alerts
    rules:
      - alert: HighAnomalyRate
        expr: rate(anomaly_detected_total[5m]) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High anomaly detection rate"
      
      - alert: MLPredictionSlow
        expr: histogram_quantile(0.95, ml_prediction_latency_seconds) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "ML predictions are slow"
```

## 7. Troubleshooting

### Migration Issues

If migration fails:
```bash
# Check current migration status
alembic current

# View migration history
alembic history

# Rollback if needed
alembic downgrade -1
```

### Model Training Issues

If model training fails:
- Check that `./models/` directory exists and is writable
- Verify all dependencies are installed: `pip install -r requirements.txt`
- Check logs for specific error messages

### VictoriaMetrics Issues

If VictoriaMetrics forwarding fails:
- Verify VictoriaMetrics is running: `curl http://victoriametrics:8428/health`
- Check `VICTORIAMETRICS_ENABLED` and `VICTORIAMETRICS_URL` in config
- Review application logs for connection errors

## 8. Production Considerations

### Model Versioning

- Models are versioned (currently v1.0.0)
- To update: Change `MODEL_VERSION` in `bgp_flap_predictor.py`
- Old models remain in `./models/` directory

### Performance

- Use ONNX runtime for faster inference: Set `use_onnx: true` in prediction requests
- Batch anomaly detection for better performance
- Consider caching predictions for frequently accessed data

### Security

- Ensure model files are not exposed publicly
- Use authentication for all ML endpoints
- Validate input data before prediction

## Summary

✅ **Completed:**
- Alembic migration setup
- Migration script for anomalies table
- VictoriaMetrics client and integration
- Model auto-training on first use
- All API endpoints functional

📋 **To Do:**
1. Run database migration
2. (Optional) Set up VictoriaMetrics
3. Test ML predictions
4. Import Grafana dashboard
5. Monitor metrics and alerts

