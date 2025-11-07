#!/bin/bash

# Start DataForge Studio Backend
# Simple script to start the backend server

set -e

# Change to project root directory
cd "$(dirname "$0")/.."
PROJECT_ROOT=$(pwd)

echo "🚀 Starting DataForge Studio Backend"
echo "====================================="
echo ""

# Check if conda is available
if ! command -v conda &> /dev/null; then
    echo "❌ Conda not found. Please install Miniconda:"
    echo "   https://docs.conda.io/en/latest/miniconda.html"
    exit 1
fi

# Check if environment exists
if ! conda env list | grep -q "dataforge-studio"; then
    echo "❌ Environment 'dataforge-studio' not found."
    echo "   Run: make setup"
    exit 1
fi

# Check if .env exists
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    echo "⚠️  Warning: .env file not found"
    echo "   Create one with your AWS credentials"
fi

echo "✅ Starting backend on http://localhost:8000"
echo ""

# Start the backend
cd "$PROJECT_ROOT"
conda run -n dataforge-studio --no-capture-output uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

