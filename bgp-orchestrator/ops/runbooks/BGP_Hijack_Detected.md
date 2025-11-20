# Runbook: BGP Hijack Detected

## Severity
**CRITICAL**

## Symptoms
- BGP prefix hijack detected by conflict detector
- Unauthorized ASN announcing prefix
- Route leaks detected
- Unexpected AS path changes

## Impact
- Traffic hijacking
- Service disruption
- Data exfiltration risk
- Reputation damage

## Detection
- Conflict detector alerts
- ML model predictions
- RIPE RIS monitoring
- AS path analysis

## Immediate Actions

### 1. Verify Hijack
```bash
# Check conflict detector logs
kubectl logs -n bgp-orchestrator deployment/bgp-orchestrator | grep -i hijack

# Query conflict database
psql -h postgres -U bgp_user -d bgp_orchestrator -c "
  SELECT * FROM conflicts 
  WHERE type = 'bgp_hijack' 
  ORDER BY detected_at DESC 
  LIMIT 10;
  "

# Check RIPE RIS data
curl "https://ris-live.ripe.net/v1/json?query=prefix:10.0.0.0/8"
```

### 2. Identify Affected Prefixes
```bash
# Get hijack details
curl -X GET "http://bgp-orchestrator:8000/api/v1/conflicts?type=hijack" \
  -H "Authorization: Bearer $TOKEN"
```

### 3. Notify Stakeholders
- **Immediate**: Security team, Network operations
- **Within 1 hour**: Management, Legal (if customer data affected)
- **Within 24 hours**: Public disclosure (if required)

## Resolution Steps

### Step 1: Immediate Mitigation
```bash
# Withdraw affected routes from our ASN
# (Manual step - requires router access)

# Update BGP filters to reject hijacked prefix
# (Manual step - requires router configuration)
```

### Step 2: Update Route Policies
```bash
# Create route filter via API
curl -X POST "http://bgp-orchestrator:8000/api/v1/routing-policies" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "block-hijacked-prefix",
    "prefix": "10.0.0.0/8",
    "action": "deny",
    "reason": "BGP hijack mitigation"
  }'
```

### Step 3: Notify Upstream Providers
```bash
# Contact upstream providers to filter hijacked routes
# Template email:
# Subject: BGP Hijack Alert - Prefix 10.0.0.0/8
# 
# We have detected a BGP hijack of prefix 10.0.0.0/8.
# Please implement filters to reject announcements from ASN XXXXX.
# 
# Details:
# - Prefix: 10.0.0.0/8
# - Legitimate Origin ASN: 65000
# - Hijacker ASN: 65001
# - Detected: [timestamp]
```

### Step 4: Update Monitoring
```bash
# Add alert for this prefix
curl -X POST "http://prometheus:9090/api/v1/alerts" \
  -H "Content-Type: application/json" \
  -d '{
    "labels": {
      "alertname": "BGP_Hijack_Prefix_10.0.0.0_8",
      "severity": "critical",
      "prefix": "10.0.0.0/8"
    },
    "annotations": {
      "summary": "BGP hijack detected for prefix 10.0.0.0/8"
    }
  }'
```

### Step 5: Document Incident
```bash
# Create incident report
# Include:
# - Detection time
# - Affected prefixes
# - Hijacker ASN
# - Mitigation steps taken
# - Timeline of events
```

## Auto-Remediation

The system can attempt auto-remediation:
- Updates route filters automatically
- Withdraws affected routes
- Updates BGP policies
- Sends notifications

If auto-remediation succeeds, incident is auto-acknowledged.

## Escalation

Escalate if:
- Multiple prefixes affected
- Customer data at risk
- Service disruption > 1 hour
- Legal/compliance concerns

## Post-Incident

1. **Root Cause Analysis**
   - How was hijack possible?
   - Why wasn't it detected earlier?
   - What filters were missing?

2. **Prevention**
   - Update RPKI validation
   - Strengthen route filters
   - Improve monitoring
   - Update ML models

3. **Communication**
   - Internal post-mortem
   - Customer notification (if required)
   - Public disclosure (if required)

## Prevention

- **RPKI Validation**: Enable RPKI ROA validation
- **Route Filters**: Strict prefix filters
- **Monitoring**: Real-time hijack detection
- **ML Models**: Train on hijack patterns
- **Regular Audits**: Review BGP policies quarterly

## Related Runbooks

- [BGP Orchestrator Down](./BGP_Orchestrator_Down.md)
- [Database Failover](./Database_Failover.md)

## References

- [MANRS](https://www.manrs.org/)
- [RIPE RIS](https://ris-live.ripe.net/)
- [RPKI](https://www.ripe.net/manage-ips-and-asns/resource-management/certification)

