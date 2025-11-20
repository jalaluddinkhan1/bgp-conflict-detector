# Runbook: Cache Clear

## Severity
**LOW to MEDIUM**

## Symptoms
- Stale data being served
- Cache hit rate dropping
- High cache memory usage
- Inconsistent data between cache and database

## Impact
- Users seeing outdated information
- Increased database load
- Performance degradation

## Detection
- Cache hit rate < 80%
- High cache memory usage
- User reports of stale data
- Monitoring alerts

## Immediate Actions

### 1. Check Cache Status
```bash
# Redis status
redis-cli -h redis INFO stats

# Cache hit rate
redis-cli -h redis INFO stats | grep keyspace_hits

# Memory usage
redis-cli -h redis INFO memory

# Connected clients
redis-cli -h redis INFO clients
```

### 2. Identify Stale Keys
```bash
# List all keys (use with caution on large caches)
redis-cli -h redis KEYS "*"

# Check specific key patterns
redis-cli -h redis KEYS "bgp:peering:*"
redis-cli -h redis KEYS "feature:*"
```

## Resolution Steps

### Step 1: Clear Specific Cache Keys
```bash
# Clear BGP peering cache
redis-cli -h redis --scan --pattern "bgp:peering:*" | xargs redis-cli -h redis DEL

# Clear feature store cache
redis-cli -h redis --scan --pattern "feature:*" | xargs redis-cli -h redis DEL

# Clear ML model cache
redis-cli -h redis DEL "ml:model:bgp_flap_predictor"
```

### Step 2: Clear All Cache (Use with Caution)
```bash
# Clear current database
redis-cli -h redis FLUSHDB

# Clear all databases
redis-cli -h redis FLUSHALL
```

### Step 3: Using API (if available)
```bash
# Clear cache via API endpoint
curl -X POST "http://bgp-orchestrator:8000/api/v1/admin/cache/clear" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "pattern": "bgp:peering:*",
    "confirm": true
  }'
```

### Step 4: Restart Redis (if needed)
```bash
# Kubernetes
kubectl rollout restart statefulset/redis -n bgp-orchestrator

# Docker Compose
docker-compose restart redis
```

## Automated Cache Clear (Rundeck Job)

The following Rundeck job can be used for automated cache clearing:

```yaml
# See ops/rundeck/jobs/cache-clear.yaml
```

## Post-Clear Actions

### Step 1: Verify Cache is Working
```bash
# Check cache hit rate after clear
redis-cli -h redis INFO stats | grep keyspace_hits

# Monitor for 5 minutes
watch -n 5 'redis-cli -h redis INFO stats | grep keyspace_hits'
```

### Step 2: Monitor Performance
```bash
# Check API response times
curl -w "@-" -o /dev/null -s "http://bgp-orchestrator:8000/api/v1/bgp-peerings" <<'EOF'
     time_namelookup:  %{time_namelookup}\n
        time_connect:  %{time_connect}\n
     time_starttransfer:  %{time_starttransfer}\n
                    time_total:  %{time_total}\n
EOF

# Check database load
psql -h postgres -U bgp_user -d bgp_orchestrator -c "
  SELECT * FROM pg_stat_activity 
  WHERE state = 'active' 
  ORDER BY query_start;
  "
```

### Step 3: Warm Cache (if needed)
```bash
# Pre-load frequently accessed data
curl -X POST "http://bgp-orchestrator:8000/api/v1/admin/cache/warm" \
  -H "Authorization: Bearer $TOKEN"
```

## Prevention

- **TTL Configuration**: Set appropriate TTLs for cache keys
- **Cache Invalidation**: Invalidate on data updates
- **Monitoring**: Monitor cache hit rates
- **Regular Clears**: Scheduled cache clears (if needed)
- **Memory Limits**: Set Redis memory limits

## When to Clear Cache

- After major data migrations
- After fixing data corruption
- When cache memory is exhausted
- When stale data is reported
- As part of maintenance windows

## Escalation

Escalate if:
- Cache clear doesn't resolve issue
- Performance degrades after clear
- Data inconsistency persists
- Cache service unavailable

## Related Runbooks

- [BGP Orchestrator Down](./BGP_Orchestrator_Down.md)
- [Database Failover](./Database_Failover.md)

