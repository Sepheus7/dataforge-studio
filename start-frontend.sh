#!/bin/bash

# Start DataForge Studio Frontend
# Simple script to start the frontend

set -e

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
if [ ! -d "frontend/node_modules" ]; then
    echo "📦 Installing dependencies..."
    cd frontend
    npm install
    cd ..
fi

echo "✅ Starting frontend on http://localhost:3000"
echo ""

# Start the frontend
cd /Users/romainboluda/Documents/PersonalProjects/dataforge-studio/frontend
npm run dev

