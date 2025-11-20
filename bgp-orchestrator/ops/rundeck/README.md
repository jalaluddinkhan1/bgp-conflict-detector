# Rundeck Jobs for BGP Orchestrator

This directory contains Rundeck job definitions for automated incident response and operations.

## Jobs

### 1. Clear Redis Cache (`cache-clear.yaml`)
- **Purpose**: Clear Redis cache keys
- **Options**:
  - `cache_pattern`: Redis key pattern (default: "*")
  - `confirm`: Confirmation required
- **Usage**: Run when cache needs to be cleared

### 2. Restart BGP Session (`restart-bgp-session.yaml`)
- **Purpose**: Restart a specific BGP peering session
- **Options**:
  - `peering_id`: BGP peering ID (required)
  - `device`: Device name (optional)
  - `peer_ip`: Peer IP (optional)
- **Usage**: Run when a BGP session needs to be restarted

### 3. Failover to Backup Batfish (`failover-batfish.yaml`)
- **Purpose**: Failover from primary to backup Batfish instance
- **Options**:
  - `backup_endpoint`: Backup Batfish URL
  - `confirm`: Confirmation required
- **Usage**: Run when primary Batfish is unavailable

### 4. Generate Incident Report (`generate-incident-report.yaml`)
- **Purpose**: Generate incident report for post-mortem
- **Options**:
  - `incident_id`: Grafana OnCall incident ID
  - `start_time`: Incident start time
  - `end_time`: Incident end time (optional)
  - `output_format`: Report format (markdown/json/html)
- **Usage**: Run after incident resolution

## Setup

### 1. Import Jobs to Rundeck

```bash
# Using Rundeck CLI
rd jobs load -f ops/rundeck/jobs/*.yaml

# Or via Rundeck UI
# Projects > bgp-orchestrator > Import Jobs > Upload YAML files
```

### 2. Configure Job Options

Set the following in Rundeck:
- `RD_CONFIG_API_URL`: BGP Orchestrator API URL
- `RD_CONFIG_API_TOKEN`: API authentication token
- `RD_CONFIG_ONCALL_URL`: Grafana OnCall URL
- `RD_CONFIG_ONCALL_TOKEN`: OnCall API token

### 3. Configure Node Filters

Ensure nodes are tagged appropriately:
- `tags: redis` - Redis nodes
- `tags: bgp-orchestrator` - BGP Orchestrator nodes

## Auto-Trigger from PagerDuty

Jobs can be auto-triggered from PagerDuty alerts:

1. Configure PagerDuty webhook
2. Set up Rundeck webhook receiver
3. Map alert types to jobs:
   - `bgp_hijack` → Generate Incident Report
   - `service_down` → Restart BGP Session
   - `cache_issue` → Clear Redis Cache
   - `batfish_down` → Failover to Backup Batfish

## Integration with Grafana OnCall

Jobs can be triggered from Grafana OnCall:

```yaml
# In OnCall escalation policy
actions:
  - type: webhook
    url: http://rundeck:4440/api/38/job/{job_id}/run
    method: POST
    headers:
      X-Rundeck-Auth-Token: ${RUNDECK_TOKEN}
    body: |
      {
        "argString": "-confirm true -incident_id ${incident.id}"
      }
```

## Manual Execution

Jobs can be executed manually via:
- Rundeck UI
- Rundeck CLI: `rd run -j <job-id> -p <options>`
- API: `POST /api/38/job/{job_id}/run`

## Best Practices

1. **Test Jobs**: Test all jobs in staging before production
2. **Documentation**: Keep runbooks updated
3. **Monitoring**: Monitor job execution
4. **Permissions**: Restrict job execution to authorized users
5. **Logging**: Review job logs regularly

## Related Documentation

- [Runbooks](../runbooks/)
- [Grafana OnCall Integration](../../backend/alerting/oncall.py)

