# BGP Conflict Detection System

A complete system for detecting concurrent BGP configuration changes to prevent conflicts in network automation workflows.

## Features

- 🔍 **Real-time Conflict Detection**: Detects concurrent changes to BGP sessions and route-maps
- 🚨 **GitLab CI Integration**: Automatically checks for conflicts in merge requests
- 🧪 **Comprehensive Test Suite**: 5 realistic test scenarios
- 🐳 **Docker Support**: Full containerized deployment
- 📊 **REST API**: FastAPI service for programmatic access
- 📝 **Detailed Reports**: JSON and GitLab-compatible artifact formats

## Project Structure

```
bgp-conflict-detector/
├── docker-compose.yml          # Infrastructure setup
├── .gitlab-ci.yml              # CI/CD pipeline
├── schemas/
│   └── bgp.yml                 # Infrahub BGP schema
├── configs/
│   └── bgp/
│       └── routers/            # BGP router configurations
├── scripts/
│   ├── load_test_data.py       # Test data loader
│   ├── detect_bgp_conflicts.py # Main detection engine
│   ├── simulate_concurrent_change.py
│   ├── simulate_flapping.py
│   └── run_all_demos.py        # Test orchestrator
├── api/
│   ├── Dockerfile
│   ├── bgp_conflict_api.py     # FastAPI service
│   └── requirements.txt
└── tests/
    └── test_scenarios.yml      # Test scenario documentation
```

## Quick Start

### 🚀 Fastest Way to See It Work (No Docker Needed!)

```bash
python demo_without_docker.py
```

This runs a demo showing conflict detection in action - **no setup required!**

### 📖 Full Instructions

**See [HOW_TO_RUN.md](HOW_TO_RUN.md) for complete step-by-step instructions!**

### Quick Commands

```bash
# Option 1: Demo without Docker (30 seconds)
python demo_without_docker.py

# Option 2: Full system with Docker
docker-compose up -d
python scripts/load_test_data.py
python scripts/run_all_demos.py

# Option 3: Automated runner (Windows)
.\demo-runner.ps1

# Option 4: Automated runner (Linux/Mac)
chmod +x demo-runner.sh && ./demo-runner.sh
```

### Prerequisites

- **For demo**: Python 3.11+ (that's it!)
- **For full system**: Docker Desktop + Python 3.11+

### Manual Setup

1. **Start Infrastructure**:
   ```bash
   docker-compose up -d
   ```

2. **Load BGP Schema**:
   ```bash
   infrahubctl schema load schemas/bgp.yml
   ```

3. **Load Test Data**:
   ```bash
   python3 scripts/load_test_data.py
   ```

4. **Run Conflict Detection**:
   ```bash
   python3 scripts/detect_bgp_conflicts.py --diff-files "configs/bgp/routers/router01.yaml"
   ```

## Usage

### GitLab CI Integration

The system automatically runs on merge requests. Add to your `.gitlab-ci.yml`:

```yaml
include:
  - project: 'network-automation/bgp-conflict-detector'
    file: '.gitlab-ci.yml'
```

### API Service

Start the API service:

```bash
cd api
docker build -t bgp-conflict-api .
docker run -p 8001:8001 bgp-conflict-api
```

Check for conflicts:

```bash
curl -X POST http://localhost:8001/bgp/check-conflicts \
  -H "Content-Type: application/json" \
  -d '{
    "device_names": ["router01", "router02"],
    "time_window_minutes": 5
  }'
```

## Test Scenarios

1. **Concurrent ASN Change**: Two engineers modify the same peer ASN
2. **Route Map Collision**: Route-map change affects multiple peers
3. **False Positive (Old Change)**: Old changes (>5 min) don't trigger conflicts
4. **Multi-Device Policy Conflict**: Network-wide vs device-specific changes
5. **Flapping Session Block**: Flapping sessions block new changes

## Configuration

### API Keys and Tokens

**📖 See [HOW_TO_GET_API_KEYS.md](HOW_TO_GET_API_KEYS.md) for step-by-step instructions!**

**Quick Summary:**
- **INFRAHUB_TOKEN** (Required): Default token works for local dev, or generate from Infrahub UI
- **GITLAB_TOKEN** (Optional): Only needed for MR comments, create from GitLab → Access Tokens

**For local testing, you don't need to set anything - the default token works!**

**Required:**
- `INFRAHUB_TOKEN`: Infrahub authentication token (required)

**Optional:**
- `GITLAB_TOKEN`: GitLab API token for MR comments (optional)

### Environment Variables

- `INFRAHUB_URL`: Infrahub server URL (default: `http://localhost:8000`)
- `INFRAHUB_TOKEN`: Infrahub authentication token
- `GITLAB_TOKEN`: GitLab API token (optional, for MR comments)
- `CONFLICT_WINDOW_MINUTES`: Time window for conflict detection (default: 5)
- `GIT_DIFF_FILES`: Space-separated list of changed files

### Time Window

The conflict detection window defaults to 5 minutes. Changes older than this window are ignored to reduce false positives.

## Production Deployment

See `k8s-deployment.yaml` for Kubernetes deployment example.

## License

MIT

## Contributing

Contributions welcome! Please open an issue or submit a pull request.

