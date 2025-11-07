#!/bin/bash

# DataForge Studio - Development Quick Start
# This script starts both backend and frontend in development mode

set -e

# Change to project root directory
cd "$(dirname "$0")/.."
PROJECT_ROOT=$(pwd)

echo "🚀 DataForge Studio - Development Quick Start"
echo "=============================================="
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if conda is available
if ! command -v conda &> /dev/null; then
    echo -e "${YELLOW}⚠️  Conda not found. Please install Miniconda:${NC}"
    echo "   https://docs.conda.io/en/latest/miniconda.html"
    exit 1
fi

# Check if Node.js is available
if ! command -v node &> /dev/null; then
    echo -e "${YELLOW}⚠️  Node.js not found. Please install Node.js 18+:${NC}"
    echo "   https://nodejs.org/"
    exit 1
fi

# Check if backend environment exists
if ! conda env list | grep -q "dataforge-studio"; then
    echo -e "${YELLOW}⚠️  Backend environment not found. Setting up...${NC}"
    cd "$PROJECT_ROOT/backend"
    make setup
    cd "$PROJECT_ROOT"
fi

# Check if frontend dependencies are installed
if [ ! -d "$PROJECT_ROOT/frontend/node_modules" ]; then
    echo -e "${YELLOW}⚠️  Frontend dependencies not found. Installing...${NC}"
    cd "$PROJECT_ROOT/frontend"
    npm install
    cd "$PROJECT_ROOT"
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  .env file not found. Please configure:${NC}"
    echo "   cp .env.example .env"
    echo "   # Then edit .env with your credentials"
    exit 1
fi

echo ""
echo -e "${GREEN}✅ All prerequisites met!${NC}"
echo ""
echo -e "${BLUE}Starting services...${NC}"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}🛑 Stopping services...${NC}"
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    exit 0
}

trap cleanup INT TERM

# Start backend
echo -e "${BLUE}📡 Starting backend on http://localhost:8000${NC}"
cd "$PROJECT_ROOT"
conda run -n dataforge-studio --live-stream uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
BACKEND_PID=$!

# Wait for backend to start
echo "   Waiting for backend to be ready..."
sleep 5

# Check if backend is running
if ! curl -s http://localhost:8000/healthz > /dev/null; then
    echo -e "${YELLOW}⚠️  Backend may not be running. Check backend.log${NC}"
    echo "   Continuing anyway..."
fi

# Start frontend
echo ""
echo -e "${BLUE}🎨 Starting frontend on http://localhost:3000${NC}"
cd "$PROJECT_ROOT/frontend"
npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!
cd "$PROJECT_ROOT"

# Wait for frontend to start
echo "   Waiting for frontend to be ready..."
sleep 5

echo ""
echo -e "${GREEN}✅ Services started successfully!${NC}"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${BLUE}🌐 Frontend:${NC}  http://localhost:3000"
echo -e "${BLUE}📡 Backend:${NC}   http://localhost:8000"
echo -e "${BLUE}📚 API Docs:${NC}  http://localhost:8000/v1/docs"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${GREEN}Press Ctrl+C to stop all services${NC}"
echo ""

# Keep script running
wait

