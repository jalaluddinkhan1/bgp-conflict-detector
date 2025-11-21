# Deployment Guide

## Prerequisites

- Kubernetes cluster (1.24+)
- PostgreSQL 15+
- Redis 7+
- Optional: InfluxDB, Kafka, VictoriaMetrics

## Docker Deployment

### Build Image

```bash
docker build -t bgp-detector:latest -f Dockerfile .
```

### Run Container

```bash
docker run -d \
  --name bgp-detector \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql://user:pass@host:5432/db \
  -e REDIS_URL=redis://host:6379/0 \
  -e SECRET_KEY=your-secret-key \
  bgp-detector:latest
```

## Kubernetes Deployment

### Apply ConfigMap

```bash
kubectl apply -f deployments/k8s/configmap.yml
```

### Apply Deployment

```bash
kubectl apply -f deployments/k8s/deployment.yml
```

### Apply Service

```bash
kubectl apply -f deployments/k8s/service.yml
```

## Environment Variables

See `.env.example` for all available configuration options.

### Required Variables

- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `SECRET_KEY`: Secret key for cryptography (min 32 chars)

### Optional Variables

- `VICTORIAMETRICS_ENABLED`: Enable VictoriaMetrics integration
- `KAFKA_ENABLED`: Enable Kafka streaming
- `FEATURE_STORE_ENABLED`: Enable Feast feature store
- `ONCALL_ENABLED`: Enable Grafana OnCall integration

## Database Migrations

Run Alembic migrations:

```bash
alembic upgrade head
```

Or using the migration script:

```bash
python scripts/run_migrations.py upgrade
```

## Health Checks

- **Liveness**: `GET /healthz`
- **Readiness**: `GET /readyz`

Configure in Kubernetes:

```yaml
livenessProbe:
  httpGet:
    path: /healthz
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /readyz
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
```

## Monitoring

### Prometheus Metrics

Metrics are exposed at `/metrics` endpoint.

Key metrics:
- `http_requests_total`: HTTP request count
- `http_request_duration_seconds`: Request latency
- `ml_prediction_latency_seconds`: ML prediction latency
- `anomaly_detected_total`: Anomaly detection count

### Grafana Dashboard

Import `grafana/dashboards/anomaly-detection.json` into Grafana.

## Scaling

### Horizontal Scaling

The application is stateless and can be scaled horizontally:

```bash
kubectl scale deployment bgp-detector --replicas=5
```

### Vertical Scaling

Adjust resource requests/limits in `deployment.yml`:

```yaml
resources:
  requests:
    memory: "512Mi"
    cpu: "500m"
  limits:
    memory: "2Gi"
    cpu: "2000m"
```

## Security

### TLS/HTTPS

Use ingress controller with TLS:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: bgp-detector
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
    - hosts:
        - api.example.com
      secretName: bgp-detector-tls
  rules:
    - host: api.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: bgp-detector
                port:
                  number: 8000
```

### Secrets Management

Use Kubernetes secrets for sensitive data:

```bash
kubectl create secret generic bgp-detector-secrets \
  --from-literal=secret-key='your-secret-key' \
  --from-literal=database-url='postgresql://...'
```

## Backup and Recovery

### Database Backup

```bash
pg_dump -h host -U user -d db > backup.sql
```

### Restore

```bash
psql -h host -U user -d db < backup.sql
```

## Troubleshooting

### Check Logs

```bash
kubectl logs -f deployment/bgp-detector
```

### Check Metrics

```bash
curl http://localhost:8000/metrics
```

### Verify Health

```bash
curl http://localhost:8000/health/healthz
```

