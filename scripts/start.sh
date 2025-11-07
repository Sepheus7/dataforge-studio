#!/bin/bash

# DataForge Studio - Start Everything
# This script starts both backend and frontend together

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 DataForge Studio - Starting All Services${NC}"
echo "=============================================="
echo ""

# Change to project root directory (one level up from scripts/)
cd "$(dirname "$0")/.."
PROJECT_DIR=$(pwd)

# Function to cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}🛑 Stopping all services...${NC}"
    
    # Kill background processes
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
        echo "   ✓ Backend stopped"
    fi
    
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
        echo "   ✓ Frontend stopped"
    fi
    
    # Kill any remaining processes on the ports
    lsof -ti:8000 2>/dev/null | xargs kill -9 2>/dev/null || true
    lsof -ti:3000 2>/dev/null | xargs kill -9 2>/dev/null || true
    
    echo ""
    echo -e "${GREEN}✅ All services stopped${NC}"
    exit 0
}

# Set up trap to cleanup on Ctrl+C or script exit
trap cleanup INT TERM EXIT

# Check prerequisites
echo -e "${BLUE}📋 Checking prerequisites...${NC}"

# Check conda
if ! command -v conda &> /dev/null; then
    echo -e "${RED}❌ Conda not found${NC}"
    echo "   Install from: https://docs.conda.io/en/latest/miniconda.html"
    exit 1
fi
echo "   ✓ Conda found"

# Check Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ Node.js not found${NC}"
    echo "   Install from: https://nodejs.org/"
    exit 1
fi
echo "   ✓ Node.js found"

# Check conda environment
if ! conda env list | grep -q "dataforge-studio"; then
    echo -e "${RED}❌ Conda environment 'dataforge-studio' not found${NC}"
    echo "   Run: make setup"
    exit 1
fi
echo "   ✓ Conda environment exists"

# Check .env file
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  Warning: .env file not found${NC}"
    echo "   The app will use default settings"
fi

# Check frontend dependencies
if [ ! -d "$PROJECT_DIR/frontend/node_modules" ]; then
    echo ""
    echo -e "${BLUE}📦 Installing frontend dependencies...${NC}"
    cd "$PROJECT_DIR/frontend"
    npm install
    cd "$PROJECT_DIR"
    echo "   ✓ Dependencies installed"
fi

echo ""
echo -e "${GREEN}✅ All prerequisites met!${NC}"
echo ""

# Kill any existing processes on the ports
echo -e "${BLUE}🧹 Cleaning up old processes...${NC}"
lsof -ti:8000 2>/dev/null | xargs kill -9 2>/dev/null || true
lsof -ti:3000 2>/dev/null | xargs kill -9 2>/dev/null || true
sleep 1
echo "   ✓ Ports cleared"
echo ""

# Start Backend
echo -e "${BLUE}📡 Starting backend on http://localhost:8000${NC}"
conda run -n dataforge-studio --no-capture-output \
    uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000 \
    > backend.log 2>&1 &
BACKEND_PID=$!

# Wait for backend to be ready
echo "   Waiting for backend to start..."
for i in {1..30}; do
    if curl -s http://localhost:8000/healthz > /dev/null 2>&1; then
        echo -e "   ${GREEN}✓ Backend is ready!${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "   ${RED}✗ Backend failed to start${NC}"
        echo "   Check backend.log for errors"
        exit 1
    fi
    sleep 1
done

# Start Frontend
echo ""
echo -e "${BLUE}🎨 Starting frontend on http://localhost:3000${NC}"
cd "$PROJECT_DIR/frontend"
npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!
cd "$PROJECT_DIR"

# Wait for frontend to be ready
echo "   Waiting for frontend to start..."
for i in {1..30}; do
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        echo -e "   ${GREEN}✓ Frontend is ready!${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "   ${RED}✗ Frontend failed to start${NC}"
        echo "   Check frontend.log for errors"
        exit 1
    fi
    sleep 1
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${GREEN}✅ All services are running!${NC}"
echo ""
echo -e "${BLUE}🌐 URLs:${NC}"
echo "   Frontend:  http://localhost:3000"
echo "   Backend:   http://localhost:8000"
echo "   API Docs:  http://localhost:8000/v1/docs"
echo ""
echo -e "${BLUE}📋 Logs:${NC}"
echo "   Backend:   tail -f backend.log"
echo "   Frontend:  tail -f frontend.log"
echo ""
echo -e "${BLUE}🛑 To stop:${NC}"
echo "   Press Ctrl+C in this terminal"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${YELLOW}📊 Streaming logs (Ctrl+C to stop):${NC}"
echo ""

# Stream logs from both services
tail -f backend.log -f frontend.log 2>/dev/null || sleep infinity

