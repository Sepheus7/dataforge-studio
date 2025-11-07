# DataForge Studio - Architecture Documentation

## Overview

DataForge Studio is a production-grade synthetic data generation platform powered by Agentic AI, built with LangChain/LangGraph and AWS Bedrock AgentCore.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          User Interface                          │
│                    (Next.js - Coming Soon)                       │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTPS/REST API
┌────────────────────────────▼────────────────────────────────────┐
│                     AWS Application Load Balancer                │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                          EKS Cluster                             │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                FastAPI Backend Pods (3-20)                │  │
│  │  ┌────────────────────────────────────────────────────┐  │  │
│  │  │          LangGraph Agent Orchestrator              │  │  │
│  │  │  ┌──────────┐  ┌─────────────┐  ┌──────────────┐  │  │  │
│  │  │  │  Schema  │  │  Document   │  │ Replication  │  │  │  │
│  │  │  │  Agent   │  │   Agent     │  │    Agent     │  │  │  │
│  │  │  └──────────┘  └─────────────┘  └──────────────┘  │  │  │
│  │  └────────────────────────────────────────────────────┘  │  │
│  │                                                            │  │
│  │  ┌────────────────────────────────────────────────────┐  │  │
│  │  │           Service Layer                            │  │  │
│  │  │  • Structured Data Generation                      │  │  │
│  │  │  • Document Generation                             │  │  │
│  │  │  • SDV Wrapper (Dataset Replication)              │  │  │
│  │  │  • PII Detection (spacy)                          │  │  │
│  │  │  • PII Replacement                                 │  │  │
│  │  │  • Parsers (OpenAPI, DB Schema, Documents)       │  │  │
│  │  └────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ▼                   ▼                   ▼
┌────────────────┐  ┌─────────────────┐  ┌──────────────┐
│  AWS Bedrock   │  │  ElastiCache    │  │  S3 Bucket   │
│  Claude Haiku  │  │     Redis       │  │  (Artifacts) │
│     4.5        │  │   (Session)     │  │              │
└────────────────┘  └─────────────────┘  └──────────────┘
         │
         ▼
┌────────────────┐
│   LangSmith    │
│  (Monitoring)  │
└────────────────┘
```

## Core Components

### 1. Agent Layer (LangChain/LangGraph)

#### Schema Agent
- **Purpose**: Infer data schemas from natural language prompts
- **Model**: Claude Haiku 4.5 (optimal cost/performance)
- **Pattern**: ReAct (Reasoning + Acting)
- **Tools**:
  - `analyze_prompt`: Extract entities and relationships
  - `suggest_columns`: Recommend column types
  - `infer_relationships`: Detect FK relationships
  - `validate_schema`: Check schema validity
  - `normalize_schema`: Clean and standardize schemas

#### Document Agent
- **Purpose**: Generate synthetic documents (invoices, contracts, reports)
- **Capabilities**: Template-based generation with LLM enhancement
- **Formats**: PDF, DOCX, JSON

#### Replication Agent
- **Purpose**: Replicate existing datasets with statistical fidelity
- **Tools**: SDV (Synthetic Data Vault), PII detection
- **Features**: Automatic PII replacement, quality evaluation

#### Orchestrator
- **Purpose**: Coordinate multi-agent workflows
- **Pattern**: LangGraph state machine
- **Routing**: Intent-based workflow selection

### 2. Service Layer

#### Structured Data Generation
- Multi-table generation with referential integrity
- Support for various column types (uuid, int, float, categorical, datetime, etc.)
- Deterministic seeding for reproducibility
- Foreign key enforcement
- Special modes (timeseries OHLC data)

#### PII Detection & Replacement
- **Detection**: spacy NER + regex patterns
- **PII Types**: Names, emails, phones, SSN, credit cards, locations, organizations
- **Replacement Strategies**:
  - Fake: Generate realistic replacements with Faker
  - Hash: SHA256 hashing
  - Redact: Replace with [REDACTED]
  - Tokenize: Sequential tokens (ID_001, ID_002, etc.)

#### SDV Wrapper
- **Models**: GaussianCopula, CTGAN
- **Capabilities**:
  - Single-table synthesis
  - Multi-table synthesis with relationship preservation
  - Quality evaluation metrics
  - Dataset profiling

#### Parsers
- **OpenAPI**: Extract schemas from API specifications
- **DB Schema**: Parse SQL DDL statements
- **Documents**: Infer structure from JSON/CSV

### 3. API Layer (FastAPI)

#### Endpoints

**Generation**:
- `POST /v1/generation/prompt` - Generate from natural language
- `POST /v1/generation/schema` - Generate from explicit schema
- `GET /v1/generation/{job_id}` - Get job status
- `GET /v1/generation/{job_id}/stream` - SSE streaming
- `GET /v1/generation/{job_id}/download` - Download artifacts
- `DELETE /v1/generation/{job_id}` - Cancel job

**Documents**:
- `POST /v1/documents/generate` - Generate documents
- `GET /v1/documents/{job_id}/download` - Download document

**Replication**:
- `POST /v1/replication/upload` - Upload dataset
- `POST /v1/replication/{id}/analyze` - Analyze dataset
- `POST /v1/replication/{id}/replicate` - Replicate dataset

**Streaming**:
- Server-Sent Events (SSE) for real-time progress updates
- Job status, progress percentage, and messages

### 4. Infrastructure

#### AWS Resources
- **EKS Cluster**: Kubernetes v1.28, managed node groups
- **VPC**: 3 AZs, public/private subnets, NAT gateways
- **S3**: Encrypted artifact storage with lifecycle policies
- **ElastiCache Redis**: Session state and caching
- **KMS**: Encryption keys
- **IAM**: Least-privilege roles for Bedrock and S3 access

#### Kubernetes
- **Deployments**: FastAPI backend with HPA (3-20 replicas)
- **Services**: ClusterIP for internal communication
- **Ingress**: ALB Ingress Controller
- **HPA**: CPU and memory-based autoscaling
- **Secrets**: External Secrets Operator (production)

## Data Flow

### 1. Prompt-Based Generation

```
User Prompt
    ↓
FastAPI Endpoint (/v1/generation/prompt)
    ↓
Job Manager (create job, enqueue)
    ↓
Schema Agent (infer schema from prompt)
    ↓  Tools: analyze_prompt, suggest_columns, infer_relationships
    ↓
Validation & Normalization
    ↓
Structured Data Generator
    ↓  Generate tables with Faker
    ↓  Enforce FK relationships
    ↓  Stream progress updates
    ↓
Write to S3 (CSV/JSON)
    ↓
Job Complete (notify via SSE)
    ↓
User Download
```

### 2. Dataset Replication

```
User Upload CSV
    ↓
FastAPI Endpoint (/v1/replication/upload)
    ↓
Store in temp location
    ↓
Analyze Dataset (Replication Agent)
    ↓  Profile data structure
    ↓  Detect PII (spacy)
    ↓
User Reviews Analysis
    ↓
Replicate Request (/v1/replication/{id}/replicate)
    ↓
Replace PII (if enabled)
    ↓
Train SDV Model (GaussianCopula or CTGAN)
    ↓
Generate Synthetic Data
    ↓
Evaluate Quality
    ↓
Save to S3
    ↓
Job Complete
```

## Technology Stack

### Backend
- **Framework**: FastAPI (async Python)
- **Agents**: LangChain >= 1.0, LangGraph
- **LLM**: Claude Haiku 4.5 via AWS Bedrock
- **Data Gen**: Faker, SDV (Synthetic Data Vault)
- **PII**: spacy (NER)
- **Monitoring**: LangSmith

### Infrastructure
- **Orchestration**: Kubernetes (EKS)
- **IaC**: Terraform
- **Cloud**: AWS (Bedrock, S3, ElastiCache, KMS)
- **Load Balancing**: AWS ALB
- **Autoscaling**: HPA (Horizontal Pod Autoscaler)

### Frontend (Planned)
- **Framework**: Next.js (React)
- **Deployment**: AWS Amplify / S3 + CloudFront

## Scalability

### Horizontal Scaling
- HPA scales backend pods based on CPU/memory
- Min: 3 replicas, Max: 20 replicas
- Target: 70% CPU, 80% memory

### Vertical Scaling
- Per-pod resources: 2-4 GB RAM, 1-2 CPU cores
- Configurable via Kubernetes resource limits

### Job Management
- Async job processing with background tasks
- Job status tracking in-memory (can move to Redis)
- Streaming progress updates via SSE

## Security

### Authentication
- API key-based authentication (X-API-Key header)
- Future: OAuth2, JWT

### Encryption
- At rest: KMS encryption for S3 and Redis
- In transit: TLS for all communications
- Secrets: External Secrets Operator

### Network
- Private subnets for workloads
- Security groups with least privilege
- VPC endpoints for AWS services

### IAM
- IRSA (IAM Roles for Service Accounts)
- Least privilege principles
- Separate roles for backend and agents

## Monitoring & Observability

### LangSmith
- Agent trace visualization
- Performance metrics
- Evaluation datasets
- Debugging interface

### CloudWatch
- Container Insights for EKS
- Custom metrics (jobs/sec, generation time)
- Logs aggregation
- Alarms for Redis, EKS health

### Metrics
- Job completion rate
- Average generation time
- API latency (p50, p95, p99)
- Error rates by type

## Performance

### Target Metrics
- Schema inference: < 5s
- Small dataset (1k rows): < 10s
- Medium dataset (100k rows): < 2 min
- Large dataset (1M rows): < 20 min
- API latency (p95): < 500ms

### Optimizations
- Async/await throughout
- Streaming progress updates
- Efficient CSV writing
- Connection pooling for Redis
- S3 multipart uploads for large files

## Future Enhancements

1. **Advanced Agents**
   - Multi-step reasoning for complex schemas
   - Tool learning and adaptation
   - Human-in-the-loop workflows

2. **Enhanced Generation**
   - Constraint satisfaction (business rules)
   - Cross-column correlations
   - Time-series forecasting
   - Graph data generation

3. **Additional Features**
   - Unstructured data (PDFs, images)
   - Real-time streaming generation
   - Collaborative editing
   - Version control for schemas

4. **Platform**
   - Multi-tenancy
   - Usage quotas and billing
   - Template marketplace
   - Integration APIs

## References

- [LangChain Documentation](https://python.langchain.com/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [AWS Bedrock](https://aws.amazon.com/bedrock/)
- [SDV Documentation](https://docs.sdv.dev/)
- [EKS Best Practices](https://aws.github.io/aws-eks-best-practices/)

