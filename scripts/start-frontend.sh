#!/bin/bash

# Start DataForge Studio Frontend
# Simple script to start the frontend

set -e

# Change to project root directory
cd "$(dirname "$0")/.."
PROJECT_ROOT=$(pwd)

echo "🎨 Starting DataForge Studio Frontend"
echo "======================================"
echo ""

# Check if Node.js is available
if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found. Please install Node.js 18+:"
    echo "   https://nodejs.org/"
    exit 1
fi

# Check if dependencies are installed
if [ ! -d "$PROJECT_ROOT/frontend/node_modules" ]; then
    echo "📦 Installing dependencies..."
    cd "$PROJECT_ROOT/frontend"
    npm install
    cd "$PROJECT_ROOT"
fi

echo "✅ Starting frontend on http://localhost:3000"
echo ""

# Start the frontend
cd "$PROJECT_ROOT/frontend"
npm run dev

