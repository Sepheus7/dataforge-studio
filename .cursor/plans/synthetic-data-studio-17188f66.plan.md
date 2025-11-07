<!-- 17188f66-c2de-422c-80ba-095dbe9557b7 9b412d29-a1ba-4904-9f8c-42ea6fbca728 -->
# Synthetic Data Studio with Agentic AI

## Architecture Overview

**Deployment Strategy**: AWS Bedrock AgentCore + EKS (Kubernetes) for hands-on experience

- **Frontend**: Next.js/React serverless (AWS Amplify or S3+CloudFront)
- **Backend**: FastAPI on EKS with horizontal pod autoscaling
- **Agent Runtime**: AWS Bedrock AgentCore with LangChain/LangGraph (>=1.0)
- **LLM Model**: Claude Haiku 4.5 (optimal performance/reasoning balance)
- **Evaluation**: LangSmith for agent testing and monitoring
- **Storage**: S3 for artifacts, ElastiCache/Redis for session state
- **Streaming**: Server-Sent Events (SSE) via FastAPI for real-time updates

## Phase 1: Core Architecture Rebuild

### 1.1 Project Structure Redesign

Create new project structure in a fresh directory `dataforge-studio/`:

```
dataforge-studio/
├── backend/
│   ├── app/
│   │   ├── agents/           # LangChain agent definitions
│   │   │   ├── __init__.py
│   │   │   ├── schema_agent.py       # Schema inference agent
│   │   │   ├── document_agent.py     # Document generation agent
│   │   │   ├── replication_agent.py  # Dataset replication agent
│   │   │   ├── tools.py              # Shared agent tools
│   │   │   └── orchestrator.py       # Multi-agent orchestrator
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── routes_generation.py  # Data generation endpoints
│   │   │   ├── routes_documents.py   # Document generation endpoints
│   │   │   ├── routes_replication.py # Dataset replication endpoints
│   │   │   └── routes_streaming.py   # SSE streaming endpoints
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py             # Pydantic settings
│   │   │   ├── auth.py               # API key auth
│   │   │   └── streaming.py          # SSE utilities
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── generation/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── structured.py     # Table generation
│   │   │   │   ├── documents.py      # Document generation
│   │   │   │   └── sdv_wrapper.py    # SDV integration
│   │   │   ├── pii/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── detector.py       # Spacy-based PII detection
│   │   │   │   └── replacer.py       # PII replacement strategies
│   │   │   ├── parsers/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── openapi.py        # OpenAPI spec parser
│   │   │   │   ├── db_schema.py      # DB schema parser
│   │   │   │   └── document.py       # Document parser
│   │   │   ├── jobs.py               # Job management
│   │   │   └── memory.py             # AgentCore memory integration
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── requests.py           # Pydantic request models
│   │   │   ├── responses.py          # Pydantic response models
│   │   │   └── schemas.py            # Schema definitions
│   │   └── main.py
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── test_agents.py
│   │   ├── test_services.py
│   │   ├── test_api.py
│   │   └── test_pii.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── pyproject.toml
├── infrastructure/
│   ├── terraform/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── eks.tf
│   │   ├── bedrock_agentcore.tf
│   │   ├── s3.tf
│   │   └── networking.tf
│   ├── k8s/
│   │   ├── backend-deployment.yaml
│   │   ├── backend-service.yaml
│   │   ├── hpa.yaml
│   │   └── ingress.yaml
│   └── helm/
│       └── dataforge/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── chat/
│   │   │   ├── schema-editor/
│   │   │   ├── document-preview/
│   │   │   └── streaming-status/
│   │   ├── pages/
│   │   ├── services/
│   │   └── styles/
│   ├── public/
│   ├── package.json
│   ├── tsconfig.json
│   └── next.config.js
├── docs/
│   ├── architecture.md
│   ├── agent-design.md
│   ├── api-reference.md
│   └── deployment.md
├── .env.example
├── .gitignore
├── Makefile
└── README.md
```

### 1.2 Dependencies Setup

Create `backend/requirements.txt`:

```
# Core framework
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
pydantic>=2.0.0
pydantic-settings>=2.0.0

# LangChain/LangGraph (>= 1.0 for robustness)
langchain>=1.0.0
langchain-aws>=1.0.0
langgraph>=1.0.0
langchain-community>=1.0.0
langchain-core>=1.0.0
langsmith>=0.1.0  # For evaluation and agent testing

# AWS
boto3>=1.40.0
botocore>=1.40.0

# Data generation
Faker>=37.0.0
sdv[copula]>=1.26.0
pandas>=2.3.0
numpy>=2.0.0

# PII detection with spacy
spacy>=3.7.0

# Document generation
python-docx>=1.1.0
pypdf2>=3.0.1
reportlab>=4.2.0
openpyxl>=3.1.2

# Streaming
sse-starlette>=2.1.0

# OpenAPI parsing
openapi-spec-validator>=0.7.1
prance>=23.6.0

# Utilities
python-multipart  # File uploads
aiofiles  # Async file ops
redis>=5.0.0  # For caching
httpx>=0.27.0  # Async HTTP client
```

Create `backend/pyproject.toml` for development tools:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.black]
line-length = 100

[tool.ruff]
line-length = 100
```

### 1.3 Configuration Management

Create `backend/app/core/config.py`:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="allow")
    
    # API
    API_KEY: str = "dev-key"
    API_PREFIX: str = "/v1"
    
    # AWS Bedrock AgentCore
    AWS_REGION: str = "us-east-1"
    BEDROCK_AGENT_ID: Optional[str] = None
    BEDROCK_AGENT_ALIAS_ID: Optional[str] = None
    
    # LLM Configuration - Claude Haiku 4.5
    LLM_PROVIDER: str = "bedrock"
    LLM_MODEL: str = "anthropic.claude-3-5-haiku-20241022:0"
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 4096
    
    # LangSmith (for agent evaluation & testing)
    LANGCHAIN_TRACING_V2: bool = True
    LANGCHAIN_API_KEY: Optional[str] = None
    LANGCHAIN_PROJECT: str = "dataforge-studio"
    
    # Storage
    S3_BUCKET: Optional[str] = None
    S3_REGION: str = "us-east-1"
    LOCAL_ARTIFACTS_DIR: str = "artifacts"
    
    # Redis/Memory
    REDIS_URL: str = "redis://localhost:6379"
    
    # Generation limits
    MAX_ROWS_PER_TABLE: int = 1_000_000
    MAX_TABLES: int = 50
    MAX_COLUMNS_PER_TABLE: int = 200
    
    # Spacy model for PII detection
    SPACY_MODEL: str = "en_core_web_sm"

settings = Settings()
```

### 1.4 Initial Setup Files

Create `.env.example`:

```
# API
API_KEY=your-api-key-here

# AWS
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key

# LangSmith
LANGCHAIN_API_KEY=your-langsmith-key
LANGCHAIN_PROJECT=dataforge-studio

# Storage
S3_BUCKET=dataforge-artifacts-dev

# Redis
REDIS_URL=redis://localhost:6379
```

Create `Makefile`:

```makefile
.PHONY: setup dev test clean

setup:
	python -m venv .venv
	. .venv/bin/activate && pip install -r backend/requirements.txt
	python -m spacy download en_core_web_sm

dev:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	cd backend && pytest tests/ -v

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
```

## Phase 2: Agent Implementation with LangChain/LangGraph

### 2.1 Schema Inference Agent

Build in `backend/app/agents/schema_agent.py` using Claude Haiku 4.5:

- Use LangGraph ReAct pattern with tools
- Tools: analyze_prompt, suggest_columns, infer_relationships, validate_schema
- LangSmith integration for tracing
- Stream agent thoughts via SSE

### 2.2 Document Generation Agent

Build in `backend/app/agents/document_agent.py`:

- Generate invoices, contracts, reports from prompts
- Template-based generation with LLM enhancement
- Export to PDF/DOCX/JSON

### 2.3 Replication Agent

Build in `backend/app/agents/replication_agent.py`:

- Analyze uploaded datasets with SDV
- Detect PII with spacy
- Train synthesizer and generate synthetic data
- Validate statistical fidelity

### 2.4 Multi-Agent Orchestrator

Build in `backend/app/agents/orchestrator.py`:

- LangGraph StateGraph coordinating agents
- Route based on user intent
- Shared memory and context

## Phase 3: Service Layer

### 3.1 Structured Data Generation

Migrate and enhance from existing `generation.py` into `backend/app/services/generation/structured.py`

### 3.2 PII Detection with Spacy

Build `backend/app/services/pii/detector.py`:

- Load spacy model (en_core_web_sm)
- Detect PERSON, ORG, GPE, EMAIL, PHONE, SSN, CREDIT_CARD
- Return detected PII by column

### 3.3 SDV Wrapper

Build `backend/app/services/generation/sdv_wrapper.py`:

- Wrap GaussianCopula, CTGAN models
- Single-table and multi-table synthesis
- Quality evaluation metrics

## Phase 4: API Layer with Streaming

### 4.1 Core API Endpoints

Implement in `backend/app/api/`:

- `routes_generation.py`: POST /prompt, POST /schema, GET /{job_id}
- `routes_documents.py`: POST /generate, GET /{job_id}/download
- `routes_replication.py`: POST /upload, POST /{id}/analyze, POST /{id}/replicate
- `routes_streaming.py`: GET /{job_id}/stream (SSE)

### 4.2 Main Application

Build `backend/app/main.py`:

- FastAPI app with CORS
- Include routers
- Health check endpoint
- LangSmith integration middleware

## Next Steps After Phase 1

1. Set up basic project structure
2. Install dependencies and configure environment
3. Implement core agents with LangChain >=1.0
4. Build service layer with spacy PII detection
5. Create API endpoints with streaming
6. Test with LangSmith UI
7. Deploy to local Kubernetes (minikube) first
8. Set up AWS infrastructure with Terraform
9. Deploy to EKS
10. Build Next.js frontend

## Key Technical Decisions

- **LangChain >=1.0**: More robust, better structured outputs, improved tool calling
- **Claude Haiku 4.5**: Best balance of speed, cost, and reasoning for agent tasks
- **LangSmith**: Essential for debugging agents, viewing traces, testing in UI
- **Spacy**: Lightweight, fast PII detection without heavy models
- **Complete Rebuild**: Clean slate allows modern architecture patterns
- **EKS**: Hands-on Kubernetes experience, better for long-running jobs than Lambda

## Implementation Order (Step-by-Step)

**Step 1**: Project scaffolding - create directory structure, config files

**Step 2**: Core dependencies - requirements.txt, environment setup

**Step 3**: Configuration layer - Settings, environment variables

**Step 4**: Schema Agent - first agent with LangChain 1.0 + LangSmith

**Step 5**: Service layer - migrate existing generation code

**Step 6**: API layer - FastAPI routes with streaming

**Step 7**: Testing - unit tests with LangSmith integration

**Step 8**: Local deployment - Docker + docker-compose

**Step 9**: Infrastructure - Terraform for AWS resources

**Step 10**: Production deployment - EKS with Helm

### To-dos

- [ ] Create fresh project structure in dataforge-studio/ with all directories and __init__.py files
- [ ] Set up requirements.txt, pyproject.toml, Makefile, and install dependencies including spacy model
- [ ] Implement config.py with pydantic-settings, create .env.example, set up LangSmith integration
- [ ] Build Schema Agent with LangChain >=1.0, Claude Haiku 4.5, LangGraph ReAct pattern, and LangSmith tracing
- [ ] Migrate generation service, implement PII detector with spacy, create SDV wrapper, build parsers
- [ ] Create FastAPI routes with SSE streaming, implement job management, add authentication
- [ ] Write tests for agents, services, and APIs with LangSmith integration for agent evaluation
- [ ] Create Dockerfile, docker-compose.yml for local development and testing
- [ ] Write Terraform for EKS, Bedrock AgentCore, S3, Redis, and networking
- [ ] Create Kubernetes manifests, Helm charts, deploy to EKS, configure monitoring