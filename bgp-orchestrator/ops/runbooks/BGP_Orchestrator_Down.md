# Runbook: BGP Orchestrator Service Down

## Severity
**CRITICAL**

## Symptoms
- BGP Orchestrator API is not responding
- Health check endpoint returns 5xx errors
- No metrics being collected
- Users cannot access the service

## Impact
- Cannot create or manage BGP peerings
- Real-time conflict detection unavailable
- ML predictions unavailable
- Feature store serving unavailable

## Detection
- Health check endpoint: `GET /healthz`
- Readiness check: `GET /readyz`
- Prometheus metrics: `up{job="bgp-orchestrator"} == 0`
- Grafana dashboard alerts

## Immediate Actions

### 1. Verify Service Status
```bash
# Check pod status (Kubernetes)
kubectl get pods -n bgp-orchestrator -l app=bgp-orchestrator

# Check service logs
kubectl logs -n bgp-orchestrator deployment/bgp-orchestrator --tail=100

# Check health endpoint
curl -v http://bgp-orchestrator:8000/healthz
```

### 2. Check Dependencies
```bash
# Database connectivity
kubectl exec -n bgp-orchestrator deployment/bgp-orchestrator -- \
  psql -h postgres -U bgp_user -d bgp_orchestrator -c "SELECT 1;"

# Redis connectivity
kubectl exec -n bgp-orchestrator deployment/bgp-orchestrator -- \
  redis-cli -h redis ping
```

### 3. Check Resource Usage
```bash
# CPU and memory
kubectl top pods -n bgp-orchestrator

# Check for OOM kills
kubectl get events -n bgp-orchestrator --sort-by='.lastTimestamp' | grep OOM
```

## Resolution Steps

### Step 1: Restart Service
```bash
# Kubernetes
kubectl rollout restart deployment/bgp-orchestrator -n bgp-orchestrator

# Docker Compose
docker-compose restart bgp-orchestrator
```

### Step 2: If Restart Fails
```bash
# Check application logs for errors
kubectl logs -n bgp-orchestrator deployment/bgp-orchestrator --tail=500 | grep -i error

# Check configuration
kubectl get configmap bgp-orchestrator-config -n bgp-orchestrator -o yaml

# Verify environment variables
kubectl get deployment bgp-orchestrator -n bgp-orchestrator -o jsonpath='{.spec.template.spec.containers[0].env}'
```

### Step 3: Database Issues
```bash
# Check database connection pool
kubectl exec -n bgp-orchestrator deployment/bgp-orchestrator -- \
  psql -h postgres -U bgp_user -d bgp_orchestrator -c "
  SELECT count(*) FROM pg_stat_activity WHERE datname = 'bgp_orchestrator';
  "

# Check for locks
kubectl exec -n bgp-orchestrator deployment/bgp-orchestrator -- \
  psql -h postgres -U bgp_user -d bgp_orchestrator -c "
  SELECT * FROM pg_locks WHERE NOT granted;
  "
```

### Step 4: Redis Issues
```bash
# Check Redis memory usage
redis-cli -h redis INFO memory

# Check Redis connections
redis-cli -h redis INFO clients

# Clear Redis if needed (use with caution)
redis-cli -h redis FLUSHDB
```

### Step 5: Scale Up (if resource constrained)
```bash
# Increase replicas
kubectl scale deployment bgp-orchestrator -n bgp-orchestrator --replicas=3

# Increase resources
kubectl set resources deployment bgp-orchestrator -n bgp-orchestrator \
  --requests=cpu=1000m,memory=2Gi \
  --limits=cpu=2000m,memory=4Gi
```

## Escalation

If service is still down after 15 minutes:
1. Escalate to Platform Team
2. Check for infrastructure issues (network, storage)
3. Consider failover to backup region (if available)

## Post-Incident

1. Review logs for root cause
2. Update monitoring alerts if needed
3. Document lessons learned
4. Update this runbook if new patterns discovered

## Prevention

- Set up health check monitoring
- Configure resource limits appropriately
- Implement circuit breakers
- Regular load testing
- Database connection pool monitoring

## Related Runbooks

- [Database Failover](./Database_Failover.md)
- [Cache Clear](./Cache_Clear.md)

