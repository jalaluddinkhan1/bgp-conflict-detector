# Status Page Configuration

This directory contains configuration for Cachet status page.

## Setup

### 1. Deploy Cachet

```bash
docker-compose -f docker-compose.status.yml up -d
```

### 2. Configure Components

Import components from `cachet-config.yaml`:

```bash
# Using Cachet API
curl -X POST http://cachet:8000/api/v1/components \
  -H "X-Cachet-Token: YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d @cachet-config.yaml
```

### 3. Update Status

Update component status via API:

```bash
# Mark component as down
curl -X PUT http://cachet:8000/api/v1/components/1 \
  -H "X-Cachet-Token: YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": 4}'  # 4 = Major Outage
```

## Integration with Monitoring

Automatically update status page from Prometheus alerts:

```yaml
# prometheus-alerts.yml
groups:
  - name: status_page
    rules:
      - alert: UpdateStatusPage
        expr: up{job="bgp-orchestrator"} == 0
        for: 5m
        annotations:
          summary: "Update status page - service down"
        # Webhook to Cachet API
```

## Public URL

Status page is typically available at:
- `https://status.example.com`
- `https://status.bgp.example.com`

## Related Documentation

- [Cachet Documentation](https://docs.cachethq.io/)
- [Runbooks](../runbooks/)

