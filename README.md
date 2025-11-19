# 🔍 BGP Conflict Detection System

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

**Automatically detect and prevent BGP configuration conflicts in network automation workflows**

[Features](#-features) • [Quick Start](#-quick-start) • [Documentation](#-documentation) • [Examples](#-examples)

</div>

---

## 📋 Table of Contents

- [What is This?](#-what-is-this)
- [Why Do You Need This?](#-why-do-you-need-this)
- [Features](#-features)
- [How It Works](#-how-it-works)
- [Quick Start](#-quick-start)
- [Installation](#-installation)
- [Usage Examples](#-usage-examples)
- [Project Structure](#-project-structure)
- [Configuration](#-configuration)
- [API Documentation](#-api-documentation)
- [Testing](#-testing)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)

---

## 🎯 What is This?

The **BGP Conflict Detection System** is an intelligent tool that prevents network engineers from accidentally making conflicting changes to BGP (Border Gateway Protocol) configurations at the same time.

### Real-World Problem It Solves

Imagine this scenario:
- **Engineer A** modifies a BGP session in Git
- **Engineer B** modifies the same BGP session in Infrahub (at the same time)
- Both changes get deployed → **Network outage!** 💥

This system detects these conflicts **before** they cause problems and alerts the engineers to coordinate their changes.

---

## 💡 Why Do You Need This?

### Common Problems Without This System:

❌ **Concurrent Changes**: Two engineers modify the same BGP peer simultaneously  
❌ **Route-Map Conflicts**: Changes to route-maps affect multiple sessions unexpectedly  
❌ **Silent Failures**: Conflicts go unnoticed until production deployment  
❌ **Network Outages**: Conflicting configurations cause BGP sessions to fail  
❌ **Rollback Chaos**: Hard to identify which change caused the problem  

### Benefits With This System:

✅ **Early Detection**: Conflicts detected before deployment  
✅ **Automatic Alerts**: GitLab MR comments notify engineers immediately  
✅ **Time Window**: Only flags recent changes (configurable, default 5 minutes)  
✅ **Multiple Conflict Types**: Detects session, route-map, and policy conflicts  
✅ **CI/CD Integration**: Automatically runs in your GitLab pipeline  
✅ **Detailed Reports**: JSON reports with conflict details and severity levels  

---

## ✨ Features

### 🔍 Conflict Detection
- **Direct Session Conflicts**: Detects when the same BGP session is modified by multiple engineers
- **Route-Map Collisions**: Identifies when route-map changes affect multiple peers
- **Policy Conflicts**: Catches network-wide vs device-specific policy conflicts
- **Flapping Detection**: Blocks changes to unstable/flapping BGP sessions

### 🚨 GitLab CI Integration
- Automatically runs on every merge request
- Posts detailed conflict warnings as MR comments
- Fails pipeline if high-severity conflicts are detected
- Generates JSON reports as CI artifacts

### 🧪 Comprehensive Testing
- 5 realistic test scenarios included
- Automated test suite with demo runner
- Simulation tools for testing concurrent changes
- Flapping session simulation

### 🐳 Docker Support
- Complete containerized setup
- One-command deployment with docker-compose
- Includes Infrahub, Memgraph, RabbitMQ, and Redis
- Production-ready API service

### 📊 REST API
- FastAPI-based service
- Programmatic conflict checking
- Real-time conflict detection
- Health check endpoints

---

## 🔄 How It Works

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│   Git Changes   │         │   Infrahub API   │         │  Conflict       │
│   (Engineer A)  │────────▶│   (Engineer B)   │────────▶│  Detection      │
│                 │         │   Recent Changes │         │  Engine         │
└─────────────────┘         └──────────────────┘         └─────────────────┘
                                                                     │
                                                                     ▼
                                                          ┌─────────────────┐
                                                          │  GitLab MR      │
                                                          │  Comment +      │
                                                          │  Pipeline Fail  │
                                                          └─────────────────┘
```

### Step-by-Step Process:

1. **Engineer A** makes changes to BGP configs in Git
2. **Engineer A** creates a merge request
3. **GitLab CI** triggers the conflict detection script
4. **System queries Infrahub** for recent changes (last 5 minutes)
5. **System compares** Git changes with Infrahub changes
6. **If conflicts found**:
   - Posts warning comment on MR
   - Fails the pipeline
   - Generates detailed report
7. **Engineers coordinate** and resolve conflicts before merging

---

## 🚀 Quick Start

### Option 1: See It Work in 30 Seconds (No Docker Needed!)

```bash
python demo_without_docker.py
```

This runs a demo showing how conflict detection works - **no setup required!**

### Option 2: Full System with Docker (5 minutes)

```bash
# 1. Start infrastructure
docker-compose up -d

# 2. Load test data
python scripts/load_test_data.py

# 3. Run demo scenarios
python scripts/run_all_demos.py
```

### Option 3: Automated Runner (Windows)

```powershell
.\demo-runner.ps1
```

### Option 4: Automated Runner (Linux/Mac)

```bash
chmod +x demo-runner.sh
./demo-runner.sh
```

---

## 📦 Installation

### Prerequisites

**For Demo (No Docker):**
- ✅ Python 3.11 or higher
- ✅ That's it!

**For Full System:**
- ✅ Python 3.11 or higher
- ✅ Docker Desktop ([Install Guide](INSTALL_DOCKER.md))
- ✅ Git

### Step 1: Clone the Repository

```bash
git clone https://github.com/jalaluddinkhan1/bgp-conflict-detector.git
cd bgp-conflict-detector
```

### Step 2: Install Python Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Install Docker (For Full System)

See [INSTALL_DOCKER.md](INSTALL_DOCKER.md) for detailed instructions.

**Quick install:**
1. Download: https://www.docker.com/products/docker-desktop
2. Install and restart your computer
3. Start Docker Desktop

### Step 4: Verify Installation

```bash
python validate_setup.py
```

---

## 💻 Usage Examples

### Example 1: Detect Conflicts in Git Changes

```bash
# Set environment variables
export INFRAHUB_URL="http://localhost:8000"
export INFRAHUB_TOKEN="your-token-here"
export GIT_DIFF_FILES="configs/bgp/routers/router01.yaml"

# Run detection
python scripts/detect_bgp_conflicts.py
```

**Output:**
```
🚀 BGP Conflict Detection Engine Starting...
📄 Analyzing Git change: configs/bgp/routers/router01.yaml
🔍 Found BGP changes for devices: ['router01']
🔍 Found 1 recent BGP changes in Infrahub
❌ 1 conflicts detected!

{
  "severity": "HIGH",
  "type": "direct_session_conflict",
  "device": "router01",
  "session": "router01_192.168.1.2",
  "changed_by": "engineer-b@company.com",
  "description": "BGP session was recently modified by engineer-b@company.com"
}
```

### Example 2: Use the REST API

```bash
# Start API service
docker-compose up -d conflict_api

# Check for conflicts
curl -X POST http://localhost:8001/bgp/check-conflicts \
  -H "Content-Type: application/json" \
  -d '{
    "device_names": ["router01", "router02"],
    "time_window_minutes": 5
  }'
```

**Response:**
```json
{
  "conflicts_found": true,
  "conflict_count": 1,
  "conflicts": [
    {
      "type": "bgp_session_recently_modified",
      "session_name": "router01_192.168.1.2",
      "device": "router01",
      "changed_by": "engineer-b@company.com"
    }
  ],
  "checked_at": "2025-01-19T10:30:00"
}
```

### Example 3: Simulate Concurrent Changes

```bash
# Simulate Engineer B making a change
python scripts/simulate_concurrent_change.py \
  --session router01_192.168.1.2 \
  --field peer_asn \
  --value 65099

# Now Engineer A's Git change will detect the conflict
python scripts/detect_bgp_conflicts.py \
  --diff-files "configs/bgp/routers/router01.yaml"
```

### Example 4: GitLab CI Integration

Add to your `.gitlab-ci.yml`:

```yaml
include:
  - project: 'your-group/bgp-conflict-detector'
    file: '.gitlab-ci.yml'

variables:
  INFRAHUB_URL: "https://infrahub.yourcompany.com"
  INFRAHUB_TOKEN: "${INFRAHUB_TOKEN}"  # Set in CI/CD variables
```

The system will automatically:
- ✅ Run on every merge request
- ✅ Post conflict warnings as MR comments
- ✅ Fail pipeline if conflicts found
- ✅ Generate conflict reports

---

## 📁 Project Structure

```
bgp-conflict-detector/
│
├── 📄 README.md                    # This file - start here!
├── 📄 HOW_TO_RUN.md               # Detailed run instructions
├── 📄 INSTALL_DOCKER.md           # Docker installation guide
├── 📄 API_KEYS.md                 # API key setup guide
│
├── 🐳 docker-compose.yml          # Infrastructure setup
├── 🔧 .gitlab-ci.yml              # CI/CD pipeline
├── 📋 requirements.txt            # Python dependencies
│
├── 📂 schemas/
│   └── bgp.yml                    # Infrahub BGP schema definition
│
├── 📂 configs/
│   └── bgp/
│       └── routers/               # Sample BGP router configurations
│           ├── router01.yaml
│           └── router02.yaml
│
├── 📂 scripts/
│   ├── detect_bgp_conflicts.py    # 🎯 Main conflict detection engine
│   ├── load_test_data.py          # Load test data into Infrahub
│   ├── run_all_demos.py           # Run all test scenarios
│   ├── simulate_concurrent_change.py  # Simulate concurrent changes
│   └── simulate_flapping.py       # Simulate BGP session flapping
│
├── 📂 api/
│   ├── bgp_conflict_api.py        # FastAPI REST service
│   ├── Dockerfile                 # API container definition
│   └── requirements.txt           # API dependencies
│
├── 📂 tests/
│   └── test_scenarios.yml         # Test scenario documentation
│
├── 🚀 demo-runner.sh              # Automated demo runner (Linux/Mac)
├── 🚀 demo-runner.ps1             # Automated demo runner (Windows)
├── 🎬 demo_without_docker.py      # Quick demo (no Docker needed)
└── ✅ validate_setup.py           # Verify installation
```

---

## ⚙️ Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `INFRAHUB_URL` | No | `http://localhost:8000` | Infrahub server URL |
| `INFRAHUB_TOKEN` | ✅ Yes | `18795e9c-b6db-fbff-cf87-10652e494a9a` | Infrahub API token |
| `GITLAB_TOKEN` | ❌ No | None | GitLab token for MR comments |
| `CONFLICT_WINDOW_MINUTES` | No | `5` | Time window for conflict detection |
| `GIT_DIFF_FILES` | No | Empty | Space-separated changed files |

### Setting Environment Variables

**Windows PowerShell:**
```powershell
$env:INFRAHUB_TOKEN="your-token-here"
$env:INFRAHUB_URL="http://localhost:8000"
```

**Linux/Mac:**
```bash
export INFRAHUB_TOKEN="your-token-here"
export INFRAHUB_URL="http://localhost:8000"
```

**Or use .env file:**
```bash
# Copy example
cp .env.example .env

# Edit .env with your values
```

### API Keys Setup

📖 **See [API_KEYS.md](API_KEYS.md) for detailed token setup instructions**

**Quick Summary:**
- **INFRAHUB_TOKEN**: Required - Get from Infrahub UI → Settings → API Tokens
- **GITLAB_TOKEN**: Optional - Only needed for MR comments

---

## 📚 API Documentation

### REST API Endpoints

#### Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-19T10:30:00",
  "cache_size": 0
}
```

#### Check Conflicts
```http
POST /bgp/check-conflicts
Content-Type: application/json

{
  "device_names": ["router01", "router02"],
  "time_window_minutes": 5,
  "check_route_maps": true
}
```

**Response:**
```json
{
  "conflicts_found": true,
  "conflict_count": 1,
  "conflicts": [...],
  "checked_at": "2025-01-19T10:30:00"
}
```

### Start API Service

```bash
# Using Docker Compose
docker-compose up -d conflict_api

# Or manually
cd api
pip install -r requirements.txt
python bgp_conflict_api.py
```

API will be available at: `http://localhost:8001`

---

## 🧪 Testing

### Run All Test Scenarios

```bash
python scripts/run_all_demos.py
```

### Test Scenarios Included

1. **Concurrent ASN Change** - Two engineers change same peer ASN
2. **Route Map Collision** - Route-map change affects multiple peers
3. **False Positive (Old Change)** - Old changes don't trigger conflicts
4. **Multi-Device Policy Conflict** - Network-wide vs device-specific
5. **Flapping Session Block** - Flapping sessions block new changes

### Expected Output

```
🧪 BGP Conflict Detection Demo Suite
============================================================
🧪 SCENARIO: Concurrent ASN Change
✅ Expected 1 conflicts, found 1

🧪 SCENARIO: Route Map Collision
✅ Expected 1 conflicts, found 1

📊 DEMO SUITE SUMMARY
✅ Concurrent ASN Change: PASS
✅ Route Map Collision: PASS
✅ Multi-Device Policy Conflict: PASS
✅ Flapping Session Block: PASS

📈 Results: 4/4 scenarios passed
🎉 All scenarios passed!
```

---

## 🔧 Troubleshooting

### Docker Issues

**Problem:** Docker not starting
```bash
# Check Docker is running
docker ps

# Check logs
docker-compose logs

# Restart Docker Desktop
```

**Problem:** Port already in use
```bash
# Windows
netstat -ano | findstr :8000

# Linux/Mac
lsof -i :8000
```

### Infrahub Connection Issues

**Problem:** "Connection refused" to Infrahub
```bash
# Check Infrahub is running
curl http://localhost:8000/api/info

# Check logs
docker-compose logs infrahub

# Wait longer (can take 60+ seconds to start)
```

**Problem:** "Authentication failed"
- ✅ Check `INFRAHUB_TOKEN` is set correctly
- ✅ Verify token hasn't expired
- ✅ Check token has proper permissions

### Python Package Issues

**Problem:** Import errors
```bash
# Reinstall packages
pip install -r requirements.txt

# Or install individually
pip install httpx pyyaml gql[requests] infrahub-sdk
```

### GitLab CI Issues

**Problem:** "GitLab MR context not available"
- ✅ This is normal if running locally (not in GitLab CI)
- ✅ Set `GITLAB_TOKEN` only if you want MR comments
- ✅ System works fine without it

---

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes**
4. **Test your changes**: `python scripts/run_all_demos.py`
5. **Commit your changes**: `git commit -m 'Add amazing feature'`
6. **Push to the branch**: `git push origin feature/amazing-feature`
7. **Open a Pull Request**

### Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/bgp-conflict-detector.git
cd bgp-conflict-detector

# Install dependencies
pip install -r requirements.txt

# Run tests
python scripts/run_all_demos.py

# Make changes and test
```

---

## 📖 Additional Documentation

- **[HOW_TO_RUN.md](HOW_TO_RUN.md)** - Detailed run instructions
- **[INSTALL_DOCKER.md](INSTALL_DOCKER.md)** - Docker installation guide
- **[API_KEYS.md](API_KEYS.md)** - API key setup guide
- **[HOW_TO_GET_API_KEYS.md](HOW_TO_GET_API_KEYS.md)** - Step-by-step token creation
- **[PUSH_TO_GITHUB.md](PUSH_TO_GITHUB.md)** - GitHub push instructions

---

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 🙏 Acknowledgments

- Built with [Infrahub](https://github.com/opsmill/infrahub) for network data management
- Uses [FastAPI](https://fastapi.tiangolo.com/) for the REST API
- Docker-based infrastructure for easy deployment

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/jalaluddinkhan1/bgp-conflict-detector/issues)
- **Questions**: Open a discussion on GitHub
- **Documentation**: Check the docs folder for detailed guides

---

<div align="center">

**Made with ❤️ for network engineers**

⭐ **Star this repo if you find it useful!** ⭐

</div>
