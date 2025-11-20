# Runbook: Database Failover

## Severity
**HIGH**

## Symptoms
- Database connection errors
- High query latency
- Connection pool exhaustion
- Primary database unreachable

## Impact
- Service degradation
- Read-only mode (if read replicas available)
- Potential data loss (if not properly replicated)

## Detection
- Database health checks failing
- High error rate in logs
- Prometheus alerts: `db_connections_active > threshold`
- Connection timeout errors

## Immediate Actions

### 1. Verify Database Status
```bash
# Check primary database
psql -h postgres-primary -U bgp_user -d bgp_orchestrator -c "SELECT 1;"

# Check replication status
psql -h postgres-primary -U bgp_user -d bgp_orchestrator -c "
  SELECT * FROM pg_stat_replication;
  "

# Check database size
psql -h postgres-primary -U bgp_user -d bgp_orchestrator -c "
  SELECT pg_size_pretty(pg_database_size('bgp_orchestrator'));
  "
```

### 2. Check Replica Status
```bash
# Check replica lag
psql -h postgres-replica -U bgp_user -d bgp_orchestrator -c "
  SELECT EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp())) AS lag_seconds;
  "

# Verify replica is in recovery mode
psql -h postgres-replica -U bgp_user -d bgp_orchestrator -c "
  SELECT pg_is_in_recovery();
  "
```

## Failover Steps

### Step 1: Promote Replica (if primary is down)
```bash
# On replica server
sudo -u postgres pg_ctl promote -D /var/lib/postgresql/data

# Verify promotion
psql -h postgres-replica -U bgp_user -d bgp_orchestrator -c "
  SELECT pg_is_in_recovery();
  "  # Should return false
```

### Step 2: Update Application Configuration
```bash
# Update DATABASE_URL environment variable
# Change from: postgresql://postgres-primary:5432/bgp_orchestrator
# To: postgresql://postgres-replica:5432/bgp_orchestrator

# Kubernetes
kubectl set env deployment/bgp-orchestrator \
  DATABASE_URL=postgresql://postgres-replica:5432/bgp_orchestrator \
  -n bgp-orchestrator

# Restart pods to pick up new configuration
kubectl rollout restart deployment/bgp-orchestrator -n bgp-orchestrator
```

### Step 3: Verify Application Connectivity
```bash
# Check health endpoint
curl http://bgp-orchestrator:8000/readyz

# Check database queries
kubectl exec -n bgp-orchestrator deployment/bgp-orchestrator -- \
  python -c "
  from app.dependencies import get_db_engine
  engine = get_db_engine()
  # Test query
  "
```

### Step 4: Update DNS/Service Discovery
```bash
# If using Kubernetes service
kubectl patch service postgres -n bgp-orchestrator \
  -p '{"spec":{"selector":{"role":"primary"}}}'

# Update to point to new primary
kubectl patch service postgres -n bgp-orchestrator \
  -p '{"spec":{"selector":{"role":"replica","promoted":"true"}}}'
```

## Post-Failover

### Step 1: Verify Data Integrity
```bash
# Check record counts
psql -h postgres-replica -U bgp_user -d bgp_orchestrator -c "
  SELECT 
    'bgp_peerings' as table_name, 
    COUNT(*) as count 
  FROM bgp_peerings
  UNION ALL
  SELECT 'anomalies', COUNT(*) FROM anomalies;
  "

# Compare with backups (if available)
```

### Step 2: Set Up New Replica
```bash
# Once primary is fixed, set up new replica
# Follow PostgreSQL replication setup guide
```

### Step 3: Update Monitoring
```bash
# Update Prometheus targets
# Update Grafana dashboards
# Verify alerts are working
```

## Rollback (if needed)

If failover causes issues:
```bash
# Revert to original primary (if fixed)
kubectl set env deployment/bgp-orchestrator \
  DATABASE_URL=postgresql://postgres-primary:5432/bgp_orchestrator \
  -n bgp-orchestrator

kubectl rollout restart deployment/bgp-orchestrator -n bgp-orchestrator
```

## Prevention

- **Regular Backups**: Daily automated backups
- **Replication Monitoring**: Monitor replica lag
- **Connection Pooling**: Proper pool sizing
- **Health Checks**: Regular database health checks
- **Failover Testing**: Quarterly failover drills

## Escalation

Escalate if:
- Data loss detected
- Failover takes > 30 minutes
- Multiple databases affected
- Cannot restore service

## Related Runbooks

- [BGP Orchestrator Down](./BGP_Orchestrator_Down.md)
- [Cache Clear](./Cache_Clear.md)

