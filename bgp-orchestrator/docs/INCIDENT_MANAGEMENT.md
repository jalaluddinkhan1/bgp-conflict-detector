# Incident Management Guide

This document describes the incident management system for BGP Orchestrator using Grafana OnCall, Rundeck, and Slack.

## Architecture

```
Alert/Incident
     ↓
Grafana OnCall
     ↓
┌────┴────┐
↓         ↓
Slack   Rundeck
NOC     (Auto-Remediation)
Alerts
```

## Components

### 1. Grafana OnCall Integration

**Location**: `backend/alerting/oncall.py`

**Features**:
- Incident creation and management
- Escalation policies
- On-call rotations
- Auto-acknowledgment on remediation

**Configuration**:
```bash
ONCALL_ENABLED=true
ONCALL_URL=http://oncall:8080
ONCALL_API_TOKEN=your-token
ONCALL_SCHEDULE_NAME=bgp-orchestrator-oncall
```

### 2. Slack Integration

**Features**:
- Alerts sent to #noc-alerts channel
- Rich formatting with severity colors
- Incident ID tracking

**Configuration**:
```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

### 3. Rundeck Automation

**Location**: `ops/rundeck/jobs/`

**Available Jobs**:
- Clear Redis Cache
- Restart BGP Session
- Failover to Backup Batfish
- Generate Incident Report

## Usage

### Creating an Incident

```python
from alerting.oncall import get_incident_manager, AlertSeverity

incident_manager = get_incident_manager()

# Handle BGP hijack
incident_id = await incident_manager.handle_bgp_hijack(
    hijack_details={
        "prefix": "10.0.0.0/8",
        "origin_asn": 65000,
        "hijacker_asn": 65001,
        "detected_at": "2024-01-01T00:00:00Z",
    },
    auto_remediate=True,  # Attempt auto-remediation
)

# Handle service down
incident_id = await incident_manager.handle_service_down(
    service_name="bgp-orchestrator",
    error_message="Database connection failed",
)
```

### Auto-Remediation

The system can automatically attempt remediation:
- Updates route filters
- Withdraws affected routes
- Updates BGP policies
- Restarts services

If auto-remediation succeeds, the incident is automatically acknowledged.

### Escalation Policies

Escalation policies are configured in Grafana OnCall:

1. **Level 1**: Primary on-call engineer (5 minutes)
2. **Level 2**: Secondary on-call engineer (15 minutes)
3. **Level 3**: Team lead (30 minutes)
4. **Level 4**: Management (1 hour)

## Runbooks

Runbooks are located in `ops/runbooks/`:

- [BGP Orchestrator Down](../ops/runbooks/BGP_Orchestrator_Down.md)
- [BGP Hijack Detected](../ops/runbooks/BGP_Hijack_Detected.md)
- [Database Failover](../ops/runbooks/Database_Failover.md)
- [Cache Clear](../ops/runbooks/Cache_Clear.md)

## Rundeck Jobs

### Triggering Jobs from OnCall

Jobs can be auto-triggered from Grafana OnCall alerts:

1. Configure webhook in OnCall escalation policy
2. Map alert types to Rundeck jobs
3. Jobs execute automatically on alert

### Manual Execution

```bash
# Clear cache
rd run -j cache-clear-redis -p "cache_pattern=bgp:peering:*" -p "confirm=true"

# Restart BGP session
rd run -j restart-bgp-session -p "peering_id=123"

# Generate incident report
rd run -j generate-incident-report \
  -p "incident_id=abc123" \
  -p "start_time=2024-01-01T00:00:00Z" \
  -p "output_format=markdown"
```

## Status Page

Status page configuration is in `ops/status-page/`.

Update status via API:

```bash
curl -X PUT http://cachet:8000/api/v1/components/1 \
  -H "X-Cachet-Token: YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": 4}'  # 4 = Major Outage
```

## Best Practices

1. **Immediate Response**: Acknowledge incidents within 5 minutes
2. **Documentation**: Update runbooks with lessons learned
3. **Communication**: Keep stakeholders informed
4. **Post-Mortem**: Conduct post-mortem for all critical incidents
5. **Continuous Improvement**: Update processes based on incidents

## Monitoring

Monitor incident management:
- Incident creation rate
- Time to acknowledgment
- Time to resolution
- Auto-remediation success rate
- Escalation frequency

## Related Documentation

- [Runbooks](../ops/runbooks/)
- [Rundeck Jobs](../ops/rundeck/)
- [Status Page](../ops/status-page/)

