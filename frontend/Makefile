.PHONY: help install dev build start clean type-check lint

help:
	@echo "DataForge Studio Frontend - Available Commands:"
	@echo ""
	@echo "  make install     - Install dependencies"
	@echo "  make dev         - Start development server"
	@echo "  make build       - Build for production"
	@echo "  make start       - Start production server"
	@echo "  make lint        - Run linter"
	@echo "  make type-check  - Run TypeScript type checking"
	@echo "  make clean       - Clean build artifacts"
	@echo ""

install:
	@echo "📦 Installing dependencies..."
	npm install

dev:
	@echo "🚀 Starting development server..."
	@echo "Frontend will be available at http://localhost:3000"
	npm run dev

build:
	@echo "🔨 Building for production..."
	npm run build

start:
	@echo "▶️  Starting production server..."
	npm start

lint:
	@echo "🔍 Running linter..."
	npm run lint

type-check:
	@echo "🔎 Running TypeScript type check..."
	npm run type-check

clean:
	@echo "🧹 Cleaning build artifacts..."
	rm -rf .next node_modules .turbo
	@echo "✨ Clean complete!"

