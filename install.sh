#!/bin/bash

# Sinhala ASR Transcription Service - Installation Script
# This script installs dependencies and prepares the backend API environment

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Transcription Service Installation${NC}"
echo -e "${BLUE}  (Backend API)${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

if ! command_exists python3; then
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    echo -e "${YELLOW}Please install Python 3.8 or higher${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo -e "${GREEN}✓ Python $PYTHON_VERSION found${NC}"

# Check for pip
if ! command_exists pip3; then
    echo -e "${RED}Error: pip3 is not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ pip3 found${NC}\n"

# Create Python virtual environment if it doesn't exist
if [ ! -d "$SCRIPT_DIR/.venv" ]; then
    echo -e "${YELLOW}Creating Python virtual environment...${NC}"
    cd "$SCRIPT_DIR"
    python3 -m venv .venv
    echo -e "${GREEN}✓ Virtual environment created${NC}\n"
else
    echo -e "${GREEN}✓ Virtual environment already exists${NC}\n"
fi

# Install dependencies
echo -e "${YELLOW}Installing Python dependencies...${NC}"
cd "$SCRIPT_DIR"
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate
echo -e "${GREEN}✓ Dependencies installed${NC}\n"

# Check for .env file
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    echo -e "${YELLOW}⚠️  Warning: .env file not found${NC}"
    if [ -f "$SCRIPT_DIR/.env.example" ]; then
        echo -e "${YELLOW}Creating .env from .env.example...${NC}"
        cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
        echo -e "${GREEN}✓ .env file created${NC}"
        echo -e "${YELLOW}⚠️  Please edit .env and configure your settings:${NC}"
        echo -e "   - DATABASE_URL"
        echo -e "   - GCS_BUCKET_NAME"
        echo -e "   - SERVICE_ACCOUNT_B64 (optional)\n"
    else
        echo -e "${YELLOW}⚠️  Please create a .env file with required settings:${NC}"
        echo -e "   - DATABASE_URL"
        echo -e "   - GCS_BUCKET_NAME"
        echo -e "   - SERVICE_ACCOUNT_B64 (optional)\n"
    fi
else
    echo -e "${GREEN}✓ .env file exists${NC}\n"
fi

# Create output directories if they don't exist
mkdir -p "$SCRIPT_DIR/logs"
echo -e "${GREEN}✓ Log directory created${NC}\n"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Installation Complete!${NC}"
echo -e "${GREEN}========================================${NC}\n"

echo -e "${BLUE}Next steps:${NC}"
echo -e "1. Configure your .env file (if not already done)"
echo -e "2. Run: ${GREEN}./start.sh${NC} to start the service\n"
