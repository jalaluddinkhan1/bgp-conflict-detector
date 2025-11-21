#!/bin/bash
# Development helper script

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 BGP Conflict Detector - Development Helper${NC}"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install/update dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install -r requirements.txt
pip install -e ".[dev]"

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Creating .env file from .env.example...${NC}"
    cp .env.example .env
    echo -e "${GREEN}Please edit .env with your configuration${NC}"
fi

# Run database migrations
echo -e "${YELLOW}Running database migrations...${NC}"
alembic upgrade head

# Run tests
echo -e "${YELLOW}Running tests...${NC}"
pytest tests/ -v

# Run linting
echo -e "${YELLOW}Running linting...${NC}"
black --check .
ruff check .
mypy .

echo -e "${GREEN}✅ Development environment ready!${NC}"
echo -e "${GREEN}Run 'python -m app.main' to start the server${NC}"

