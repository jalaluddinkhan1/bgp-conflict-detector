#!/bin/bash
set -e

echo "🚀 BGP Conflict Detection Full Test Suite"
echo "========================================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check dependencies
echo "📋 Checking dependencies..."
command -v docker-compose >/dev/null 2>&1 || { echo "❌ docker-compose required"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "❌ python3 required"; exit 1; }

# Start infrastructure
echo -e "\n${YELLOW}🏗️  Starting infrastructure...${NC}"
docker-compose up -d

# Wait for Infrahub
echo -e "\n${YELLOW}⏳ Waiting for Infrahub to be ready...${NC}"
for i in {1..30}; do
    if curl -s http://localhost:8000/api/info >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Infrahub is ready!${NC}"
        break
    fi
    echo "  Attempt $i/30..."
    sleep 2
done

# Install Python dependencies
echo -e "\n${YELLOW}📦 Installing Python dependencies...${NC}"
pip3 install -q httpx pyyaml gql[requests] infrahub-sdk

# Load test data
echo -e "\n${YELLOW}📦 Loading test data...${NC}"
python3 scripts/load_test_data.py

# Run demo scenarios
echo -e "\n${YELLOW}🧪 Running demo scenarios...${NC}"
python3 scripts/run_all_demos.py

# Cleanup
echo -e "\n${YELLOW}🧹 Cleaning up...${NC}"
docker-compose down

echo -e "\n${GREEN}🎉 Demo suite complete!${NC}"

