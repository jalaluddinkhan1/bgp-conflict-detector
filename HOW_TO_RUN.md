# How to Run the BGP Conflict Detection System

## Quick Start (3 Options)

### Option 1: Demo Without Docker (Fastest - 30 seconds)

**Perfect for seeing how it works without installing Docker!**

```bash
# Run the demo
python demo_without_docker.py
```

This shows the conflict detection logic in action without needing Docker/Infrahub.

---

### Option 2: Full System with Docker (Complete - 5 minutes)

**For the full experience with real Infrahub integration**

#### Prerequisites:
1. **Install Docker Desktop**
   - Download: https://www.docker.com/products/docker-desktop
   - Install and start Docker Desktop
   - Wait for Docker to be running (whale icon in system tray)

2. **Verify Docker is running:**
   ```bash
   docker --version
   docker-compose --version
   ```

#### Steps:

**Step 1: Start Infrastructure**
```bash
docker-compose up -d
```

This starts:
- Infrahub (port 8000)
- Memgraph database (port 7687)
- RabbitMQ (ports 5672, 15672)
- Redis (port 6379)

**Step 2: Wait for Infrahub to be ready (30-60 seconds)**
```bash
# Check if ready
curl http://localhost:8000/api/info

# Or check logs
docker-compose logs infrahub
```

**Step 3: Load BGP Schema**
```bash
# If you have infrahubctl installed
infrahubctl schema load schemas/bgp.yml

# Or use the API directly (schema is auto-loaded on first use)
```

**Step 4: Load Test Data**
```bash
python scripts/load_test_data.py
```

Expected output:
```
Infrahub is ready!
Created device: router01
Created device: router02
Created device: router03
Created BGP instance for router01
Created BGP session: router01_192.168.1.2
Test data loaded successfully!
```

**Step 5: Run Demo Scenarios**
```bash
python scripts/run_all_demos.py
```

This runs 5 test scenarios showing different conflict types.

**Step 6: Stop Infrastructure (when done)**
```bash
docker-compose down
```

---

### Option 3: Use Demo Runner Script (Automated)

**Windows PowerShell:**
```powershell
.\demo-runner.ps1
```

**Linux/Mac:**
```bash
chmod +x demo-runner.sh
./demo-runner.sh
```

This script:
- Checks dependencies
- Starts Docker containers
- Waits for Infrahub
- Installs Python packages
- Loads test data
- Runs all demos
- Cleans up

---

## Individual Script Usage

### 1. Conflict Detection Script

```bash
# Basic usage
python scripts/detect_bgp_conflicts.py

# With custom parameters
python scripts/detect_bgp_conflicts.py \
  --diff-files "configs/bgp/routers/router01.yaml" \
  --window-minutes 5 \
  --infrahub-url http://localhost:8000 \
  --infrahub-token your-token-here
```

### 2. Load Test Data

```bash
python scripts/load_test_data.py
```

### 3. Simulate Concurrent Change

```bash
python scripts/simulate_concurrent_change.py \
  --session router01_192.168.1.2 \
  --field peer_asn \
  --value 65099
```

### 4. Simulate Flapping

```bash
python scripts/simulate_flapping.py \
  --session router01_192.168.1.2 \
  --flap-count 5 \
  --interval 2.0
```

### 5. Run All Demos

```bash
python scripts/run_all_demos.py
```

---

## API Service

### Start API Service

**Option A: Using Docker Compose (Recommended)**
```bash
# Already included in docker-compose.yml
docker-compose up -d conflict_api

# Check it's running
curl http://localhost:8001/health
```

**Option B: Manual Start**
```bash
cd api
pip install -r requirements.txt
python bgp_conflict_api.py
```

### Use API

```bash
# Check health
curl http://localhost:8001/health

# Check for conflicts
curl -X POST http://localhost:8001/bgp/check-conflicts \
  -H "Content-Type: application/json" \
  -d '{
    "device_names": ["router01", "router02"],
    "time_window_minutes": 5
  }'
```

---

## Troubleshooting

### Docker not starting?
```bash
# Check Docker is running
docker ps

# Check logs
docker-compose logs

# Restart Docker Desktop
# Then try again: docker-compose up -d
```

### Infrahub not ready?
```bash
# Wait longer (can take 60+ seconds)
docker-compose logs -f infrahub

# Check if port 8000 is in use
netstat -an | findstr 8000  # Windows
lsof -i :8000               # Linux/Mac
```

### Python package errors?
```bash
# Install all requirements
pip install -r requirements.txt

# Or install individually
pip install httpx pyyaml gql[requests] infrahub-sdk
```

### Connection refused errors?
```bash
# Make sure Infrahub is running
curl http://localhost:8000/api/info

# Check environment variables
echo $INFRAHUB_URL      # Linux/Mac
echo $env:INFRAHUB_URL  # Windows PowerShell

# Set if missing
export INFRAHUB_URL="http://localhost:8000"  # Linux/Mac
$env:INFRAHUB_URL="http://localhost:8000"    # Windows PowerShell
```

---

## Verify Everything Works

Run the validation script:
```bash
python validate_setup.py
```

Expected output:
```
All checks passed! System is ready to run.
```

---

## Expected Output

When running `python scripts/run_all_demos.py`, you should see:

```
BGP Conflict Detection Demo Suite
Infrahub: http://localhost:8000

Loading test data...
Created device: router01
Created BGP session: router01_192.168.1.2
Test data loaded successfully!

============================================================
SCENARIO: Concurrent ASN Change
============================================================
Setting up scenario...
Simulated: router01_192.168.1.2.peer_asn = 65100
Expected 1 conflicts, found 1

============================================================
DEMO SUITE SUMMARY
============================================================
[PASS] Concurrent ASN Change: PASS
[PASS] Route Map Collision: PASS
[PASS] Multi-Device Policy Conflict: PASS
[PASS] Flapping Session Block: PASS

Results: 4/4 scenarios passed
All scenarios passed!
```

---

## Quick Reference

| Task | Command |
|------|---------|
| **See demo** | `python demo_without_docker.py` |
| **Start everything** | `docker-compose up -d` |
| **Load test data** | `python scripts/load_test_data.py` |
| **Run all tests** | `python scripts/run_all_demos.py` |
| **Stop everything** | `docker-compose down` |
| **Check status** | `python validate_setup.py` |
| **View logs** | `docker-compose logs -f` |

---

## Next Steps

1. **Read the code**: Check `scripts/detect_bgp_conflicts.py` to understand the logic
2. **Modify scenarios**: Edit `scripts/run_all_demos.py` to add your own tests
3. **Integrate with CI/CD**: See `.gitlab-ci.yml` for GitLab integration
4. **Deploy API**: See `api/` directory for production deployment

---

## Need Help?

- Check `README.md` for overview
- Check `API_KEYS.md` for token setup
- Check `HOW_TO_GET_API_KEYS.md` for detailed token instructions
- Review error messages - they usually point to the issue!

