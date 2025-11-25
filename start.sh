#!/bin/bash

# Sinhala ASR Dataset Collection Service - Startup Script
# This script starts the transcription service

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
echo -e "${BLUE}  Sinhala ASR Service Startup${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Check if virtual environment exists
if [ ! -d "$SCRIPT_DIR/.venv" ]; then
    echo -e "${RED}Error: Virtual environment not found${NC}"
    echo -e "${YELLOW}Please run: ./install.sh${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Virtual environment verified${NC}"

# Check for .env file
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    echo -e "${YELLOW}⚠️  Warning: .env file not found${NC}"
    echo -e "${YELLOW}The service may not work correctly without proper configuration${NC}\n"
else
    echo -e "${GREEN}✓ Configuration file found${NC}"
fi

# Create log directory if it doesn't exist
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"

# Function to cleanup background processes on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down service...${NC}"
    kill $SERVER_PID 2>/dev/null
    wait $SERVER_PID 2>/dev/null
    echo -e "${GREEN}Service stopped${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start the server
echo -e "\n${BLUE}Starting FastAPI server...${NC}"
cd "$SCRIPT_DIR"
source .venv/bin/activate

echo -e "${GREEN}✓ Service started${NC}\n"
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Service Information${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Main Interface:${NC}         http://localhost:5000"
echo -e "${GREEN}API Documentation:${NC}      http://localhost:5000/docs"
echo -e "${GREEN}API ReDoc:${NC}              http://localhost:5000/redoc"
echo -e "${GREEN}Health Check:${NC}           http://localhost:5000/health"
echo -e "${GREEN}Server logs:${NC}            $LOG_DIR/server.log"
echo -e "${BLUE}========================================${NC}"
echo -e "\n${YELLOW}Press Ctrl+C to stop the service${NC}\n"

# Run uvicorn with live output
uvicorn app.main:app --reload --host 0.0.0.0 --port 5000 --log-level info 2>&1 | tee "$LOG_DIR/server.log" &
SERVER_PID=$!

# Wait for the process
wait $SERVER_PID
