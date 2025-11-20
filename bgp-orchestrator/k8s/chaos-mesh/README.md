# Chaos Mesh Configuration for BGP Orchestrator

This directory contains Chaos Mesh configurations for testing the resilience of the BGP Orchestrator under various failure conditions.

## Prerequisites

1. Kubernetes cluster with Chaos Mesh installed
2. BGP Orchestrator deployed in `bgp-orchestrator` namespace
3. Proper RBAC permissions for Chaos Mesh

## Chaos Experiments

### NetworkChaos (`network-chaos.yaml`)

Simulates network issues:
- **bgp-api-network-delay**: Adds 500ms latency to API calls (runs at 2 AM)
- **bgp-api-network-partition**: Partitions network for 5 minutes (runs at 3 AM)
- **bgp-db-network-delay**: Adds 200ms latency to database calls (runs at 4 AM)

### PodChaos (`pod-chaos.yaml`)

Simulates pod failures:
- **bgp-backend-pod-kill**: Randomly kills backend pods (runs at 1 AM)
- **bgp-backend-pod-failure**: Simulates pod failure for 2 minutes (runs at 5 AM)
- **bgp-backend-container-kill**: Kills 50% of containers (runs at 6 AM)

### IOChaos (`io-chaos.yaml`)

Simulates I/O issues:
- **postgres-slow-io**: Delays 50% of PostgreSQL I/O by 500ms (runs at 7 AM)
- **postgres-io-error**: Causes 10% of PostgreSQL I/O to fail (runs at 8 AM)
- **redis-slow-io**: Delays 30% of Redis I/O by 200ms (runs at 9 AM)

### StressChaos (`stress-chaos.yaml`)

Simulates resource stress:
- **bgp-backend-cpu-stress**: Spikes CPU to 90% for 10 minutes (runs at 10 AM)
- **bgp-backend-memory-stress**: Allocates 1Gi memory for 5 minutes (runs at 11 AM)
- **postgres-cpu-stress**: Spikes PostgreSQL CPU to 80% (runs at 12 PM)
- **bgp-backend-combined-stress**: Combined CPU and memory stress (runs at 1 PM)

## Usage

### Apply All Chaos Experiments

```bash
kubectl apply -f k8s/chaos-mesh/
```

### Apply Specific Chaos Type

```bash
# Network chaos only
kubectl apply -f k8s/chaos-mesh/network-chaos.yaml

# Pod chaos only
kubectl apply -f k8s/chaos-mesh/pod-chaos.yaml

# I/O chaos only
kubectl apply -f k8s/chaos-mesh/io-chaos.yaml

# Stress chaos only
kubectl apply -f k8s/chaos-mesh/stress-chaos.yaml
```

### Check Chaos Experiments Status

```bash
# List all chaos experiments
kubectl get networkchaos,podchaos,iochaos,stresschaos -n bgp-orchestrator

# Describe specific experiment
kubectl describe networkchaos bgp-api-network-delay -n bgp-orchestrator
```

### Delete Chaos Experiments

```bash
# Delete all
kubectl delete -f k8s/chaos-mesh/

# Delete specific experiment
kubectl delete networkchaos bgp-api-network-delay -n bgp-orchestrator
```

## Monitoring

Monitor the effects of chaos experiments:

1. **Application Metrics**: Check Prometheus/Grafana for:
   - API latency spikes
   - Error rates
   - Request failures
   - Database connection errors

2. **Kubernetes Events**: 
   ```bash
   kubectl get events -n bgp-orchestrator --sort-by='.lastTimestamp'
   ```

3. **Pod Status**:
   ```bash
   kubectl get pods -n bgp-orchestrator -w
   ```

4. **Application Logs**:
   ```bash
   kubectl logs -f deployment/bgp-orchestrator -n bgp-orchestrator
   ```

## Customization

### Adjust Schedule

Edit the `scheduler.cron` field in each experiment:

```yaml
scheduler:
  cron: "0 2 * * *"  # Format: minute hour day month weekday
```

### Adjust Intensity

Modify chaos parameters:

- **Network delay**: Change `delay.latency` value
- **Pod kill rate**: Change `mode` and `value` for random selection
- **I/O delay**: Change `delay` and `percent` values
- **CPU stress**: Change `load` percentage

### Run Once (No Schedule)

Remove the `scheduler` section to run immediately:

```yaml
# Remove this:
# scheduler:
#   cron: "0 2 * * *"
```

## Safety

⚠️ **Warning**: These chaos experiments can cause service disruption. Use in:
- Staging environments
- Dedicated test clusters
- During maintenance windows

Do NOT run in production without proper safeguards and monitoring.

## Troubleshooting

### Chaos Experiment Not Running

1. Check Chaos Mesh is installed:
   ```bash
   kubectl get pods -n chaos-mesh
   ```

2. Check experiment status:
   ```bash
   kubectl describe networkchaos <name> -n bgp-orchestrator
   ```

3. Check Chaos Mesh logs:
   ```bash
   kubectl logs -n chaos-mesh -l app.kubernetes.io/name=chaos-mesh
   ```

### Experiment Causing Too Much Disruption

1. Reduce intensity (lower percentages, shorter durations)
2. Use `mode: one` instead of `mode: all` to limit scope
3. Add more specific selectors to target fewer pods

### Need to Stop Immediately

```bash
# Delete all experiments
kubectl delete networkchaos,podchaos,iochaos,stresschaos --all -n bgp-orchestrator
```

