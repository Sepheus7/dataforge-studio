# DataForge Studio

A production-grade synthetic data studio powered by Agentic AI using LangChain/LangGraph and AWS Bedrock AgentCore.

## Features

- 🤖 **Agent-Based Schema Inference**: Natural language to data schema using Claude Haiku 4.5
- 📊 **Structured Data Generation**: Generate realistic multi-table datasets with referential integrity
- 📄 **Document Generation**: Create synthetic documents (invoices, contracts, reports)
- 🔄 **Dataset Replication**: Replicate existing datasets with SDV while replacing PII
- 🔒 **PII Detection**: Automatic PII detection and replacement using spacy
- 📡 **Real-time Streaming**: Server-Sent Events for live progress updates
- 📊 **LangSmith Integration**: Agent evaluation and monitoring

## Architecture

- **Backend**: FastAPI with async support
- **Agents**: LangChain >= 1.0 + LangGraph for multi-agent orchestration
- **LLM**: Claude Haiku 4.5 via AWS Bedrock
- **Deployment**: EKS (Kubernetes) on AWS
- **Storage**: S3 for artifacts, Redis for caching
- **Frontend**: Next.js 14 with TypeScript and Tailwind CSS

## Quick Start

### Prerequisites

- **Conda** (miniconda or anaconda) - RECOMMENDED
  - Install from: https://docs.conda.io/en/latest/miniconda.html
- Python 3.11+ (if not using conda)
- AWS credentials configured
- LangSmith API key (optional, for agent tracing)
- Redis (optional, for production)

### Setup with Conda (Recommended)

```bash
# Clone the repository
git clone <repo-url>
cd dataforge-studio

# Set up conda environment
make setup

# Activate environment
conda activate dataforge-studio

# Install spacy model
make install-spacy

# Configure environment variables
cp .env.example .env
# Edit .env with your credentials

# Run development server (backend only)
make dev

# OR: Start everything with one command (recommended!)
./scripts/start.sh
```

### Why Conda?

Conda is recommended for this project because:
- Better dependency resolution for data science packages
- Handles non-Python dependencies (system libs, spacy models)
- More robust than pip for complex package environments
- Works across platforms consistently

## Documentation

📚 **Comprehensive guides available:**

### Frontend
- **[Frontend Setup Guide](FRONTEND_SETUP.md)** - Complete frontend setup, usage, and deployment guide

### Backend & Agents
- **[LangGraph Setup & Deployment](docs/langgraph_setup.md)** - LangGraph configuration, LangSmith integration, and AWS AgentCore deployment
- **[LangSmith Chat UI](docs/langsmith_chat_ui.md)** - LangGraph Studio and agent testing
- **[AWS Setup Guide](docs/aws_setup.md)** - IAM configuration, Bedrock access, and credentials
- **[AWS Service Quotas](docs/aws_quotas.md)** - Understanding and increasing Bedrock quotas to avoid throttling

### Architecture
- **[Architecture Overview](docs/architecture.md)** - System architecture and design decisions
- **[Zero-Shot Architecture](docs/zero_shot_architecture.md)** - How the LLM-driven agent system works

### API Usage

```bash
# Generate data from natural language prompt
curl -X POST http://localhost:8000/v1/generation/prompt \
  -H "X-API-Key: dev-key" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Generate e-commerce customer, order, and transaction data",
    "size_hint": {"customers": 10000, "orders": 50000}
  }'

# Check job status
curl http://localhost:8000/v1/generation/{job_id} \
  -H "X-API-Key: dev-key"

# Stream progress (SSE)
curl http://localhost:8000/v1/generation/{job_id}/stream \
  -H "X-API-Key: dev-key"
```

### LangGraph CLI Usage

```bash
# Start LangGraph Studio with Chat UI (Recommended!)
langgraph studio
# - Select "chat" graph
# - Click "Chat" mode
# - Start chatting with your agent!

# Or start development server
langgraph dev
# Access agent API at http://localhost:8123

# View traces in LangSmith
# https://smith.langchain.com/ (if LANGCHAIN_TRACING_V2=true)
```

### Frontend Setup (Production UI)

```bash
# Start the frontend
cd frontend
npm install
npm run dev
# Frontend available at http://localhost:3000
```

See **`FRONTEND_SETUP.md`** for complete frontend setup instructions.

### Alternative: LangGraph Studio Chat UI (for agent testing)

```bash
# Option 1: Use built-in Studio Chat Mode (easiest for development!)
langgraph studio
# - Select "chat" graph
# - Click "Chat" mode
# - Start chatting with your agent!

# Option 2: Standalone Agent Chat UI
npx agent-chat-ui --url http://localhost:8123 --graph chat

# Option 3: Custom LangServe chat server
python backend/chat_server.py
```

See **`AGENT_CHAT_UI_SETUP.md`** for LangGraph Studio setup instructions.

## Project Structure

```
dataforge-studio/
├── backend/           # FastAPI backend with agents
├── frontend/          # Next.js frontend
├── infrastructure/    # Terraform, K8s, Helm
├── docs/             # Documentation
└── tests/            # Test suite
```

## Development

```bash
# Run tests
make test

# Format code
make format

# Lint
make lint

# Clean cache
make clean
```

## Deployment

### Local (Docker Compose)

```bash
docker-compose up
```

### AWS EKS

```bash
# Deploy infrastructure
cd infrastructure/terraform
terraform init
terraform apply

# Deploy application
cd ../k8s
kubectl apply -f .
```

## Documentation

- [Architecture](docs/architecture.md)
- [Agent Design](docs/agent-design.md)
- [API Reference](docs/api-reference.md)
- [Deployment Guide](docs/deployment.md)

## License

MIT

## Contributing

Contributions welcome! Please read our contributing guidelines first.

