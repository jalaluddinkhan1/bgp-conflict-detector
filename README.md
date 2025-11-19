# BGP Conflict Detection System

A production-grade system for detecting concurrent BGP configuration changes to prevent conflicts in network automation workflows. This system integrates with Infrahub and GitLab CI/CD to provide real-time conflict detection and automated validation of BGP session modifications.

## Overview

The BGP Conflict Detection System addresses a critical problem in network operations: concurrent modifications to BGP configurations by multiple engineers can lead to network outages, routing inconsistencies, and deployment failures. This system provides automated detection of such conflicts before they reach production, enabling coordination between engineering teams and preventing service disruptions.

## Architecture

The system operates on a three-tier architecture:

1. **Change Detection Layer**: Monitors Git repositories for BGP configuration changes and queries Infrahub for recent modifications
2. **Conflict Analysis Engine**: Compares temporal changes across multiple sources to identify potential conflicts
3. **Integration Layer**: Provides REST API endpoints and GitLab CI/CD integration for automated validation

### Core Components

- **Conflict Detection Engine**: Python-based service that analyzes BGP session and route-map modifications
- **Infrahub Integration**: GraphQL and REST API clients for querying network state
- **GitLab CI/CD Pipeline**: Automated validation on merge requests
- **REST API Service**: FastAPI-based service for programmatic conflict checking
- **Test Framework**: Comprehensive test suite with simulation capabilities

## Features

### Conflict Detection

- **Direct Session Conflicts**: Identifies when the same BGP session is modified by multiple engineers within a configurable time window
- **Route-Map Collisions**: Detects when route-map changes affect multiple BGP peers simultaneously
- **Policy Conflicts**: Identifies conflicts between network-wide and device-specific policy changes
- **Temporal Analysis**: Configurable time windows (default: 5 minutes) to reduce false positives

### Integration Capabilities

- **GitLab CI/CD**: Automatic validation on merge requests with detailed conflict reports
- **REST API**: Programmatic access for custom integrations and automation
- **Infrahub Integration**: Real-time querying of network state and recent changes
- **Artifact Generation**: JSON reports compatible with CI/CD artifact systems

### Testing and Validation

- Comprehensive test suite with five realistic conflict scenarios
- Simulation tools for concurrent change testing
- Automated demo runner for validation
- Test data loader for development environments

## Requirements

### System Requirements

- Python 3.11 or higher
- Docker Desktop (for full system deployment)
- Docker Compose 2.0 or higher
- Git 2.0 or higher

### Dependencies

- Infrahub SDK 1.15.1+
- FastAPI 0.104.1+
- GraphQL Client 4.0.0+
- HTTPX 0.25.2+
- PyYAML 6.0.1+

## Installation

### Quick Start

For demonstration purposes without Docker:

```bash
python demo_without_docker.py
```

### Full System Installation

1. Clone the repository:

```bash
git clone https://github.com/jalaluddinkhan1/bgp-conflict-detector.git
cd bgp-conflict-detector
```

2. Install Python dependencies:

```bash
pip install -r requirements.txt
```

3. Start infrastructure services:

```bash
docker-compose up -d
```

4. Wait for Infrahub to initialize (approximately 30-60 seconds):

```bash
curl http://localhost:8000/api/info
```

5. Load BGP schema:

```bash
infrahubctl schema load schemas/bgp.yml
```

6. Load test data:

```bash
python scripts/load_test_data.py
```

7. Run validation tests:

```bash
python scripts/run_all_demos.py
```

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `INFRAHUB_URL` | No | `http://localhost:8000` | Infrahub server URL |
| `INFRAHUB_TOKEN` | Yes | None | Infrahub API authentication token |
| `GITLAB_TOKEN` | No | None | GitLab API token for merge request comments |
| `CONFLICT_WINDOW_MINUTES` | No | `5` | Time window for conflict detection in minutes |
| `GIT_DIFF_FILES` | No | Empty | Space-separated list of changed files for analysis |

### Infrahub Token Configuration

The system requires an Infrahub API token for authentication. Configure the token using one of the following methods:

1. Environment variable:
```bash
export INFRAHUB_TOKEN="your-token-here"
```

2. Docker Compose environment:
```yaml
environment:
  INFRAHUB_TOKEN: "your-token-here"
```

3. Command-line argument:
```bash
python scripts/detect_bgp_conflicts.py --infrahub-token "your-token-here"
```

For detailed token setup instructions, refer to `API_KEYS.md`.

## Usage

### Command-Line Interface

Basic conflict detection:

```bash
python scripts/detect_bgp_conflicts.py \
  --diff-files "configs/bgp/routers/router01.yaml" \
  --window-minutes 5 \
  --infrahub-url http://localhost:8000 \
  --infrahub-token your-token-here
```

### REST API

Start the API service:

```bash
docker-compose up -d conflict_api
```

Check for conflicts:

```bash
curl -X POST http://localhost:8001/bgp/check-conflicts \
  -H "Content-Type: application/json" \
  -d '{
    "device_names": ["router01", "router02"],
    "time_window_minutes": 5,
    "check_route_maps": true
  }'
```

API Response:

```json
{
  "conflicts_found": true,
  "conflict_count": 1,
  "conflicts": [
    {
      "type": "bgp_session_recently_modified",
      "session_name": "router01_192.168.1.2",
      "device": "router01",
      "peer_ip": "192.168.1.2",
      "changed_by": "engineer@company.com",
      "changed_at": "2025-01-19T10:30:00Z"
    }
  ],
  "checked_at": "2025-01-19T10:35:00Z"
}
```

### GitLab CI/CD Integration

Add to your `.gitlab-ci.yml`:

```yaml
include:
  - project: 'your-group/bgp-conflict-detector'
    file: '.gitlab-ci.yml'

variables:
  INFRAHUB_URL: "https://infrahub.yourcompany.com"
  INFRAHUB_TOKEN: "${INFRAHUB_TOKEN}"
```

The system will automatically:
- Analyze changed files in merge requests
- Query Infrahub for recent modifications
- Post conflict warnings as MR comments
- Fail the pipeline if high-severity conflicts are detected
- Generate JSON reports as CI artifacts

## Project Structure

```
bgp-conflict-detector/
├── api/
│   ├── bgp_conflict_api.py      # FastAPI REST service
│   ├── Dockerfile                # API container definition
│   └── requirements.txt          # API dependencies
├── configs/
│   └── bgp/
│       └── routers/              # BGP router configurations
│           ├── router01.yaml
│           └── router02.yaml
├── schemas/
│   └── bgp.yml                   # Infrahub BGP schema definition
├── scripts/
│   ├── detect_bgp_conflicts.py   # Main conflict detection engine
│   ├── load_test_data.py         # Test data loader
│   ├── run_all_demos.py          # Test orchestrator
│   ├── simulate_concurrent_change.py  # Concurrent change simulator
│   └── simulate_flapping.py      # BGP session flapping simulator
├── tests/
│   └── test_scenarios.yml        # Test scenario documentation
├── docker-compose.yml            # Infrastructure orchestration
├── .gitlab-ci.yml                # CI/CD pipeline configuration
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

## Conflict Detection Algorithm

The system employs a temporal conflict detection algorithm:

1. **Change Extraction**: Parse Git diff to identify modified BGP sessions and route-maps
2. **Temporal Query**: Query Infrahub for changes within the configured time window
3. **Conflict Analysis**: Compare Git changes with Infrahub changes to identify:
   - Direct session conflicts (same session modified)
   - Route-map collisions (shared route-maps affected)
   - Policy conflicts (network-wide vs device-specific)
4. **Severity Assessment**: Classify conflicts as HIGH or MEDIUM severity
5. **Reporting**: Generate detailed reports with conflict metadata

### Time Window Configuration

The default conflict detection window is 5 minutes. Changes older than this window are ignored to reduce false positives. This window can be configured via the `CONFLICT_WINDOW_MINUTES` environment variable or command-line argument.

## Testing

### Test Scenarios

The system includes five comprehensive test scenarios:

1. **Concurrent ASN Change**: Two engineers modify the same peer ASN simultaneously
2. **Route Map Collision**: Route-map changes affect multiple peers
3. **False Positive Prevention**: Old changes (>5 minutes) do not trigger conflicts
4. **Multi-Device Policy Conflict**: Network-wide changes conflict with device-specific modifications
5. **Flapping Session Block**: Unstable sessions block new changes

### Running Tests

Execute the complete test suite:

```bash
python scripts/run_all_demos.py
```

Run individual test scenarios:

```bash
python scripts/simulate_concurrent_change.py \
  --session router01_192.168.1.2 \
  --field peer_asn \
  --value 65099
```

## API Documentation

### Endpoints

#### Health Check

```http
GET /health
```

Returns service health status and cache statistics.

#### Check Conflicts

```http
POST /bgp/check-conflicts
Content-Type: application/json
```

Request body:

```json
{
  "device_names": ["router01", "router02"],
  "time_window_minutes": 5,
  "check_route_maps": true
}
```

Response:

```json
{
  "conflicts_found": boolean,
  "conflict_count": integer,
  "conflicts": [
    {
      "type": "string",
      "session_id": "string",
      "session_name": "string",
      "device": "string",
      "peer_ip": "string",
      "changed_by": "string",
      "changed_at": "string"
    }
  ],
  "checked_at": "string"
}
```

## Deployment

### Docker Compose Deployment

The system includes a complete Docker Compose configuration for local development and testing:

```bash
docker-compose up -d
```

This starts:
- Infrahub (port 8000)
- Memgraph database (port 7687)
- RabbitMQ message queue (ports 5672, 15672)
- Redis cache (port 6379)
- Conflict Detection API (port 8001)

### Production Deployment

For production deployments, consider:

- Kubernetes deployment with proper resource limits
- External Infrahub instance configuration
- Secure token management via secrets management systems
- High availability configuration for API service
- Monitoring and logging integration

## Performance Considerations

- Conflict detection queries are optimized for sub-second response times
- GraphQL queries are used for efficient data retrieval from Infrahub
- In-memory caching reduces redundant API calls
- Time-windowed queries minimize database load

## Security

- API tokens are never logged or exposed in error messages
- Environment variables are used for sensitive configuration
- GitLab CI/CD variables should be marked as protected and masked
- Token rotation is recommended for production deployments

## Troubleshooting

### Common Issues

**Infrahub Connection Failures**

Verify Infrahub is running and accessible:

```bash
curl http://localhost:8000/api/info
```

Check token validity:

```bash
python -c "from infrahub_sdk import InfrahubClientSync; client = InfrahubClientSync(address='http://localhost:8000', token='your-token'); print('Connected')"
```

**Docker Service Issues**

Check service status:

```bash
docker-compose ps
```

View logs:

```bash
docker-compose logs infrahub
```

**Python Package Errors**

Reinstall dependencies:

```bash
pip install --upgrade -r requirements.txt
```

## Contributing

Contributions are welcome. Please follow these guidelines:

1. Fork the repository
2. Create a feature branch from `main`
3. Implement changes with appropriate tests
4. Ensure all tests pass: `python scripts/run_all_demos.py`
5. Submit a pull request with a clear description of changes

## License

This project is licensed under the MIT License.

## References

- [Infrahub Documentation](https://github.com/opsmill/infrahub)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [GitLab CI/CD Documentation](https://docs.gitlab.com/ee/ci/)

## Support

For issues, questions, or contributions, please use the GitHub issue tracker.
