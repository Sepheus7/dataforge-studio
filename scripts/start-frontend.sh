#!/bin/bash
set -e

echo "🚀 Starting Next.js Frontend..."
echo ""

# Change to frontend directory
cd "$(dirname "$0")/../frontend"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Start Next.js dev server
echo "✅ Starting Next.js on http://localhost:3000"
npm run dev
