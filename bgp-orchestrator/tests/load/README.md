# Load Testing Guide

This directory contains load testing scripts and configurations for the BGP Orchestrator.

## Tools

### K6
- **Script**: `bgp_load_test.js`
- **Language**: JavaScript
- **Best for**: High-performance, scriptable load testing
- **Metrics**: Exports to Prometheus

### Locust
- **Script**: `bgp_load_test.py`
- **Language**: Python
- **Best for**: Python-based testing, web UI
- **Metrics**: Built-in web interface

### ExaBGP
- **Config**: `exabgp/exabgp.conf`
- **Purpose**: Simulate 80K BGP peers
- **Best for**: BGP protocol testing

## Quick Start

### Using Docker Compose

```bash
# Start load testing environment
docker-compose -f docker-compose.load.yml --profile load-test up -d

# Run K6 tests
docker-compose -f docker-compose.load.yml run --rm k6 run /scripts/bgp_load_test.js

# Run Locust tests (web UI at http://localhost:8089)
docker-compose -f docker-compose.load.yml --profile load-test up locust

# Stop everything
docker-compose -f docker-compose.load.yml --profile load-test down
```

### Using K6 Directly

```bash
# Install K6
# macOS: brew install k6
# Linux: See https://k6.io/docs/getting-started/installation/
# Windows: choco install k6

# Run basic test
k6 run bgp_load_test.js

# Run with custom parameters
k6 run --vus 100 --duration 5m bgp_load_test.js

# Export to Prometheus
k6 run --out prometheus=remote_write=http://prometheus:9090/api/v1/write bgp_load_test.js
```

### Using Locust Directly

```bash
# Install Locust
pip install locust

# Run with web UI
locust -f bgp_load_test.py --host=http://localhost:8000

# Run headless
locust -f bgp_load_test.py \
  --host=http://localhost:8000 \
  --headless \
  --users 100 \
  --spawn-rate 10 \
  --run-time 5m
```

## Test Scenarios

### Scenario 1: Baseline Load
- **Users**: 50
- **Duration**: 5 minutes
- **Purpose**: Establish baseline performance

```bash
k6 run --vus 50 --duration 5m bgp_load_test.js
```

### Scenario 2: Peak Load
- **Users**: 100
- **Duration**: 10 minutes
- **Purpose**: Test under peak load

```bash
k6 run --vus 100 --duration 10m bgp_load_test.js
```

### Scenario 3: Stress Test
- **Users**: 200
- **Duration**: 15 minutes
- **Purpose**: Find breaking point

```bash
k6 run --vus 200 --duration 15m bgp_load_test.js
```

### Scenario 4: Spike Test
- **Users**: 0 → 200 → 0
- **Duration**: 10 minutes
- **Purpose**: Test sudden load spikes

```bash
k6 run --stage 0s:0,30s:200,5m:200,5m30s:0 bgp_load_test.js
```

## Metrics

### Key Metrics to Monitor

1. **Request Rate**: Requests per second
2. **Response Time**: p50, p95, p99 latencies
3. **Error Rate**: Percentage of failed requests
4. **Throughput**: Successful requests per second
5. **Resource Usage**: CPU, memory, I/O

### Prometheus Queries

```promql
# Request rate
rate(http_req_duration[5m])

# p99 latency
histogram_quantile(0.99, rate(http_req_duration_bucket[5m]))

# Error rate
rate(http_req_failed[5m])

# Success rate
rate(peering_creation_success[5m])
```

## ExaBGP Configuration

### Generate 80K BGP Peers

```bash
cd tests/load/exabgp
python generate_peers.py 80000 > exabgp-80k.conf
```

### Run ExaBGP

```bash
# Using Docker
docker-compose -f docker-compose.load.yml --profile load-test up exabgp

# Or directly
exabgp exabgp-80k.conf
```

## Best Practices

1. **Start Small**: Begin with low user counts and gradually increase
2. **Monitor Resources**: Watch CPU, memory, and I/O during tests
3. **Test Incrementally**: Don't jump from 10 to 1000 users
4. **Use Realistic Data**: Generate test data that matches production
5. **Test Recovery**: Verify system recovers after load test
6. **Document Results**: Keep records of test results and findings

## Troubleshooting

### K6 Issues

**Problem**: K6 can't connect to API
- **Solution**: Check `K6_BASE_URL` environment variable
- **Solution**: Verify API is running and accessible

**Problem**: High failure rate
- **Solution**: Check API logs for errors
- **Solution**: Verify authentication tokens
- **Solution**: Check resource limits

### Locust Issues

**Problem**: Locust web UI not accessible
- **Solution**: Check port 8089 is not in use
- **Solution**: Verify firewall rules

**Problem**: Tests running slowly
- **Solution**: Use FastHttpUser instead of HttpUser
- **Solution**: Reduce wait times between requests

### ExaBGP Issues

**Problem**: Can't generate 80K peers
- **Solution**: Use multiple ExaBGP instances
- **Solution**: Generate configuration in batches
- **Solution**: Increase system resources

## Performance Targets

Based on requirements for 80K BGP sessions:

- **API Latency**: p99 < 1 second
- **Error Rate**: < 0.1%
- **Throughput**: > 1000 requests/second
- **Availability**: > 99.9% uptime
- **Recovery Time**: < 2 minutes after failure

## Related Documentation

- [Chaos Test Runbook](../docs/CHAOS_TEST_RUNBOOK.md)
- [Monitoring Setup](../docs/MONITORING.md)
- [K6 Documentation](https://k6.io/docs/)
- [Locust Documentation](https://docs.locust.io/)

