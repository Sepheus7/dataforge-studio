.PHONY: setup dev test clean format lint help install-spacy conda-setup

help:  ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

conda-setup: ## Set up conda environment (RECOMMENDED)
	@echo "Setting up conda environment..."
	@which conda > /dev/null || (echo "ERROR: conda not found. Install miniconda or anaconda first." && exit 1)
	conda env create -f environment.yml
	@echo "Installation complete! Run 'make install-spacy' to download spacy model."
	@echo "Activate environment with: conda activate dataforge-studio"

setup: conda-setup ## Alias for conda-setup

install-spacy: ## Download spacy language model
	@echo "Downloading spacy English model..."
	@which conda > /dev/null && conda run -n dataforge-studio python -m spacy download en_core_web_sm || python -m spacy download en_core_web_sm
	@echo "Spacy model installed!"

dev: ## Run development server
	@echo "Starting development server..."
	@which conda > /dev/null && conda run -n dataforge-studio --no-capture-output uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000 || (cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000)

test: ## Run tests
	@echo "Running tests..."
	@which conda > /dev/null && conda run -n dataforge-studio pytest backend/tests/ -v --cov=backend/app --cov-report=term-missing || (cd backend && pytest tests/ -v --cov=app --cov-report=term-missing)

test-unit: ## Run unit tests only
	@which conda > /dev/null && conda run -n dataforge-studio pytest backend/tests/ -v -m unit || (cd backend && pytest tests/ -v -m unit)

test-integration: ## Run integration tests only
	@which conda > /dev/null && conda run -n dataforge-studio pytest backend/tests/ -v -m integration || (cd backend && pytest tests/ -v -m integration)

format: ## Format code with black
	@echo "Formatting code..."
	@which conda > /dev/null && conda run -n dataforge-studio black backend/app backend/tests || black backend/app backend/tests
	@echo "Code formatted!"

lint: ## Lint code with ruff
	@echo "Linting code..."
	@which conda > /dev/null && conda run -n dataforge-studio ruff check backend/app backend/tests || ruff check backend/app backend/tests
	@echo "Linting complete!"

lint-fix: ## Fix linting issues automatically
	@which conda > /dev/null && conda run -n dataforge-studio ruff check --fix backend/app backend/tests || ruff check --fix backend/app backend/tests

clean: ## Clean up cache and temporary files
	@echo "Cleaning up..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf backend/htmlcov
	rm -rf backend/.coverage
	rm -rf backend/artifacts/
	@echo "Cleanup complete!"

conda-clean: ## Remove conda environment
	@echo "Removing conda environment..."
	conda env remove -n dataforge-studio
	@echo "Conda environment removed!"

docker-build: ## Build Docker image
	docker build -t dataforge-studio:latest -f backend/Dockerfile backend/

docker-run: ## Run Docker container
	docker run -p 8000:8000 --env-file .env dataforge-studio:latest

docker-compose-up: ## Start services with docker-compose
	docker-compose up -d

docker-compose-down: ## Stop services with docker-compose
	docker-compose down

install-dev: ## Install development dependencies
	. .venv/bin/activate && pip install -e backend/[dev]

check: lint test ## Run linting and tests

all: clean format lint test ## Run all checks

