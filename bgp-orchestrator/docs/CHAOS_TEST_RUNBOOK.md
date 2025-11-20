# Chaos Test Failure Runbook

This runbook provides step-by-step procedures for diagnosing and fixing issues when chaos tests fail.

## Table of Contents

1. [Understanding Chaos Test Failures](#understanding-chaos-test-failures)
2. [Network Chaos Failures](#network-chaos-failures)
3. [Pod Chaos Failures](#pod-chaos-failures)
4. [I/O Chaos Failures](#io-chaos-failures)
5. [Stress Chaos Failures](#stress-chaos-failures)
6. [General Troubleshooting](#general-troubleshooting)
7. [Prevention Strategies](#prevention-strategies)

## Understanding Chaos Test Failures

### What is a Chaos Test Failure?

A chaos test failure occurs when:
- The application becomes unavailable during chaos experiments
- Error rates exceed acceptable thresholds (>1%)
- Recovery time exceeds SLA requirements
- Data integrity is compromised
- Service degradation is unacceptable

### Failure Indicators

Monitor these metrics during chaos tests:

- **API Availability**: < 99.9% uptime
- **Error Rate**: > 1% of requests failing
- **Latency**: p99 > 1 second
- **Database Connections**: Connection pool exhaustion
- **Pod Restart Time**: > 2 minutes
- **Data Loss**: Any data corruption or loss

## Network Chaos Failures

### Symptoms

- API requests timing out
- High latency (p99 > 1s)
- Connection errors
- Intermittent failures

### Diagnosis Steps

1. **Check Network Chaos Status**
   ```bash
   kubectl get networkchaos -n bgp-orchestrator
   kubectl describe networkchaos <chaos-name> -n bgp-orchestrator
   ```

2. **Check Pod Network Connectivity**
   ```bash
   kubectl exec -n bgp-orchestrator <pod-name> -- ping -c 3 <target-pod-ip>
   kubectl exec -n bgp-orchestrator <pod-name> -- curl -v http://<service-name>:8000/healthz
   ```

3. **Check Application Logs**
   ```bash
   kubectl logs -n bgp-orchestrator deployment/bgp-orchestrator --tail=100
   ```

4. **Check Metrics**
   - Prometheus: `rate(http_requests_total{status=~"5.."}[5m])`
   - Grafana: API latency dashboard

### Fixes

#### Fix 1: Add Connection Retries

**Problem**: Application doesn't retry failed connections

**Solution**: Implement exponential backoff retry logic

```python
# In your HTTP client code
import time
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
def make_request(url):
    return httpx.get(url, timeout=30.0)
```

#### Fix 2: Increase Timeouts

**Problem**: Default timeouts too short for network delays

**Solution**: Adjust timeout values

```python
# Database connection timeout
DATABASE_CONNECT_TIMEOUT = 30  # seconds

# HTTP client timeout
HTTP_TIMEOUT = 60  # seconds

# Redis connection timeout
REDIS_TIMEOUT = 10  # seconds
```

#### Fix 3: Implement Circuit Breaker

**Problem**: Cascading failures when network is unstable

**Solution**: Add circuit breaker pattern

```python
from circuitbreaker import circuit

@circuit(failure_threshold=5, recovery_timeout=60)
def call_external_service():
    # Your service call
    pass
```

#### Fix 4: Add Health Check Endpoints

**Problem**: Load balancer doesn't detect unhealthy pods

**Solution**: Implement comprehensive health checks

```python
@app.get("/healthz")
async def healthz():
    checks = {
        "database": await check_database(),
        "redis": await check_redis(),
        "external_apis": await check_external_apis(),
    }
    
    if all(checks.values()):
        return {"status": "healthy"}
    else:
        return Response(
            status_code=503,
            content={"status": "unhealthy", "checks": checks}
        )
```

## Pod Chaos Failures

### Symptoms

- Pods not restarting automatically
- Long recovery time (> 2 minutes)
- Service unavailable during pod restarts
- Data loss during pod termination

### Diagnosis Steps

1. **Check Pod Status**
   ```bash
   kubectl get pods -n bgp-orchestrator -w
   kubectl describe pod <pod-name> -n bgp-orchestrator
   ```

2. **Check Pod Events**
   ```bash
   kubectl get events -n bgp-orchestrator --sort-by='.lastTimestamp'
   ```

3. **Check Replica Count**
   ```bash
   kubectl get deployment bgp-orchestrator -n bgp-orchestrator
   ```

4. **Check Pod Logs**
   ```bash
   kubectl logs -n bgp-orchestrator <pod-name> --previous
   ```

### Fixes

#### Fix 1: Increase Replica Count

**Problem**: Single pod, no redundancy

**Solution**: Deploy multiple replicas

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: bgp-orchestrator
spec:
  replicas: 3  # Minimum 3 for high availability
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0  # Zero-downtime deployments
```

#### Fix 2: Add Pod Disruption Budget

**Problem**: Too many pods killed simultaneously

**Solution**: Configure PDB

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: bgp-orchestrator-pdb
spec:
  minAvailable: 2  # Always keep 2 pods available
  selector:
    matchLabels:
      app: bgp-orchestrator
```

#### Fix 3: Improve Graceful Shutdown

**Problem**: Pods terminated abruptly, losing in-flight requests

**Solution**: Implement graceful shutdown

```python
import signal
import asyncio

async def shutdown_handler():
    # Stop accepting new requests
    # Wait for existing requests to complete
    # Close database connections
    # Flush logs
    pass

def setup_signal_handlers():
    signal.signal(signal.SIGTERM, lambda s, f: asyncio.create_task(shutdown_handler()))
```

#### Fix 4: Add Readiness Probes

**Problem**: Traffic routed to pods before they're ready

**Solution**: Configure readiness probe

```yaml
readinessProbe:
  httpGet:
    path: /readyz
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 5
  timeoutSeconds: 3
  failureThreshold: 3
```

## I/O Chaos Failures

### Symptoms

- Slow database queries
- High I/O wait times
- Database connection timeouts
- Data corruption

### Diagnosis Steps

1. **Check I/O Chaos Status**
   ```bash
   kubectl get iochaos -n bgp-orchestrator
   kubectl describe iochaos <chaos-name> -n bgp-orchestrator
   ```

2. **Check Database Performance**
   ```bash
   kubectl exec -n bgp-orchestrator deployment/postgresql -- \
     psql -U bgp_user -d bgp_orchestrator -c "
     SELECT pid, state, query_start, now() - query_start as duration, query
     FROM pg_stat_activity
     WHERE state != 'idle'
     ORDER BY duration DESC;
     "
   ```

3. **Check Disk I/O**
   ```bash
   kubectl top pods -n bgp-orchestrator
   # Check for high I/O wait
   ```

4. **Check Application Logs**
   ```bash
   kubectl logs -n bgp-orchestrator deployment/bgp-orchestrator | grep -i "timeout\|error\|slow"
   ```

### Fixes

#### Fix 1: Add Query Timeouts

**Problem**: Queries hang indefinitely during I/O delays

**Solution**: Set query timeouts

```python
from sqlalchemy import event
from sqlalchemy.pool import Pool

@event.listens_for(Pool, "connect")
def set_sqlite_timeout(dbapi_conn, connection_record):
    # PostgreSQL statement timeout
    dbapi_conn.execute("SET statement_timeout = '30s'")
```

#### Fix 2: Implement Connection Pooling

**Problem**: Exhausting database connections during slow I/O

**Solution**: Configure connection pool

```python
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,           # Increase pool size
    max_overflow=40,        # Allow overflow
    pool_timeout=30,         # Wait for connection
    pool_recycle=3600,      # Recycle connections
    pool_pre_ping=True,      # Verify connections
)
```

#### Fix 3: Add Database Query Retries

**Problem**: Queries fail on transient I/O errors

**Solution**: Retry with exponential backoff

```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((OperationalError, TimeoutError))
)
async def execute_query(query):
    return await db.execute(query)
```

#### Fix 4: Use Read Replicas

**Problem**: Read queries block on slow I/O

**Solution**: Route reads to replicas

```python
# Use read replica for SELECT queries
read_db = create_async_engine(READ_REPLICA_URL)
write_db = create_async_engine(WRITE_DB_URL)

# Route reads to replica
async def get_peerings():
    async with read_db.begin() as conn:
        return await conn.execute(select(BGPPeering))
```

## Stress Chaos Failures

### Symptoms

- High CPU usage (>90%)
- High memory usage
- Slow response times
- OOM (Out of Memory) kills

### Diagnosis Steps

1. **Check Stress Chaos Status**
   ```bash
   kubectl get stresschaos -n bgp-orchestrator
   kubectl describe stresschaos <chaos-name> -n bgp-orchestrator
   ```

2. **Check Resource Usage**
   ```bash
   kubectl top pods -n bgp-orchestrator
   kubectl top nodes
   ```

3. **Check Pod Resource Limits**
   ```bash
   kubectl describe pod <pod-name> -n bgp-orchestrator | grep -A 5 "Limits\|Requests"
   ```

4. **Check Application Metrics**
   - CPU usage
   - Memory usage
   - GC (Garbage Collection) frequency
   - Response times

### Fixes

#### Fix 1: Increase Resource Limits

**Problem**: Pods hitting CPU/memory limits

**Solution**: Adjust resource requests and limits

```yaml
resources:
  requests:
    cpu: "1000m"      # 1 CPU
    memory: "2Gi"     # 2 GB RAM
  limits:
    cpu: "2000m"      # 2 CPUs
    memory: "4Gi"      # 4 GB RAM
```

#### Fix 2: Optimize Code Performance

**Problem**: Inefficient code causing high CPU usage

**Solution**: Profile and optimize

```python
# Use Pyroscope for profiling
import pyroscope

pyroscope.configure(
    application_name="bgp-orchestrator",
    server_address="http://pyroscope:4040",
)

# Optimize database queries
# - Add indexes
# - Use select_related/prefetch_related
# - Avoid N+1 queries
```

#### Fix 3: Implement Rate Limiting

**Problem**: Too many requests overwhelming the system

**Solution**: Add rate limiting

```python
from slowapi import Limiter

limiter = Limiter(key_func=get_remote_address)

@router.post("/bgp-peerings")
@limiter.limit("10/second")  # Limit to 10 requests per second
async def create_peering():
    pass
```

#### Fix 4: Add Horizontal Pod Autoscaling

**Problem**: Fixed number of pods can't handle load spikes

**Solution**: Configure HPA

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: bgp-orchestrator-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: bgp-orchestrator
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

## General Troubleshooting

### Step 1: Stop All Chaos Experiments

```bash
kubectl delete networkchaos,podchaos,iochaos,stresschaos --all -n bgp-orchestrator
```

### Step 2: Verify Application Health

```bash
# Check all pods are running
kubectl get pods -n bgp-orchestrator

# Check service endpoints
kubectl get endpoints -n bgp-orchestrator

# Test API
curl http://<service-ip>:8000/healthz
```

### Step 3: Review Logs

```bash
# Application logs
kubectl logs -n bgp-orchestrator deployment/bgp-orchestrator --tail=1000

# System logs
kubectl get events -n bgp-orchestrator --sort-by='.lastTimestamp'
```

### Step 4: Check Metrics

- Prometheus: Error rates, latency, throughput
- Grafana: Dashboards for all services
- Kubernetes: Resource usage, pod restarts

## Prevention Strategies

### 1. Regular Testing

- Run chaos tests in staging weekly
- Run full chaos suite before major releases
- Monitor and fix issues proactively

### 2. Observability

- Comprehensive logging
- Distributed tracing
- Metrics and alerting
- Continuous profiling

### 3. Resilience Patterns

- Circuit breakers
- Retries with backoff
- Timeouts and deadlines
- Graceful degradation

### 4. Resource Planning

- Right-size resource requests/limits
- Plan for peak load
- Monitor and adjust regularly

### 5. Documentation

- Keep runbooks updated
- Document known issues and fixes
- Share learnings with team

## Emergency Contacts

- **On-Call Engineer**: [Contact Info]
- **Platform Team**: [Contact Info]
- **Database Team**: [Contact Info]

## Related Documentation

- [Chaos Mesh Configuration](../k8s/chaos-mesh/README.md)
- [Load Testing Guide](../tests/load/README.md)
- [Monitoring Setup](../docs/MONITORING.md)

