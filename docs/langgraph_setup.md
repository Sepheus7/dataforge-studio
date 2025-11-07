# LangGraph Setup & Deployment Guide

This guide covers setting up DataForge Studio with LangGraph for local development, LangSmith integration, and AWS AgentCore deployment.

## Table of Contents

1. [Local Development](#local-development)
2. [LangSmith Integration](#langsmith-integration)
3. [LangGraph Configuration](#langgraph-configuration)
4. [Testing the Agent](#testing-the-agent)
5. [AWS AgentCore Deployment](#aws-agentcore-deployment)
6. [Troubleshooting](#troubleshooting)

---

## Local Development

### 1. Install LangGraph CLI

```bash
# Install LangGraph CLI globally (or in your conda env)
pip install langgraph-cli
```

### 2. Project Structure

```
dataforge-studio/
├── langgraph.json          # LangGraph configuration
├── backend/
│   ├── src/
│   │   └── agent.py        # Main agent entry point
│   ├── app/
│   │   └── agents/
│   │       ├── schema_agent.py
│   │       └── document_agent.py
│   └── requirements.txt
└── .env
```

### 3. Configuration File

The `langgraph.json` file defines your agent deployment:

```json
{
  "dependencies": ["backend"],
  "graphs": {
    "agent": "backend/src/agent.py:agent"
  },
  "env": ".env"
}
```

**Key fields:**
- `dependencies`: List of directories containing your Python code
- `graphs`: Map of graph names to Python module paths (format: `path/to/file.py:variable_name`)
- `env`: Path to environment variables file

---

## LangSmith Integration

LangSmith provides observability, tracing, and evaluation for your agents.

### 1. Get API Key

1. Go to [LangSmith](https://smith.langchain.com/)
2. Create an account or sign in
3. Navigate to Settings → API Keys
4. Create a new API key

### 2. Configure Environment

Add to your `.env` file:

```bash
# LangSmith Configuration
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_pt_xxxxxxxxxxxxx
LANGCHAIN_PROJECT=dataforge-studio
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
```

### 3. View Traces

Once configured, all agent runs will automatically appear in LangSmith:
- Go to https://smith.langchain.com/
- Navigate to your project (`dataforge-studio`)
- View traces, latency, token usage, and errors

---

## LangGraph Configuration

### Agent Structure

The unified agent (`backend/src/agent.py`) supports two task types:

#### 1. Schema Generation

```python
{
    "input": {
        "task_type": "schema",
        "prompt": "Create an ecommerce database with customers, orders, and products"
    }
}
```

#### 2. Document Generation

```python
{
    "input": {
        "task_type": "document",
        "prompt": "quarterly financial report",
        "style": "professional",
        "language": "english",
        "length": "short"
    }
}
```

### Running Locally with LangGraph

```bash
# Start LangGraph development server
langgraph dev

# This will:
# - Load your langgraph.json configuration
# - Start a local API server (default: http://localhost:8123)
# - Watch for file changes and reload
# - Enable LangSmith tracing
```

### Using LangGraph Studio

LangGraph Studio provides a visual interface for testing agents:

```bash
# Open LangGraph Studio
langgraph studio

# Or specify config file
langgraph studio --config langgraph.json
```

**Features:**
- Visual graph editor
- Interactive testing
- Real-time state inspection
- Trace visualization

---

## Testing the Agent

### 1. Direct Python Test

```bash
cd backend
python src/agent.py
```

This will run the built-in test in the `if __name__ == "__main__"` block.

### 2. LangGraph API Test

When running `langgraph dev`, test via HTTP:

```bash
# Schema generation
curl -X POST http://localhost:8123/runs/stream \
  -H "Content-Type: application/json" \
  -d '{
    "assistant_id": "agent",
    "input": {
      "input": {
        "task_type": "schema",
        "prompt": "Create a customer database"
      },
      "output": {"task_type": "", "result": {}, "error": null},
      "messages": []
    }
  }'
```

### 3. Python SDK Test

```python
from langgraph_sdk import get_client

client = get_client(url="http://localhost:8123")

# Run the agent
result = await client.runs.create(
    assistant_id="agent",
    input={
        "input": {
            "task_type": "schema",
            "prompt": "Create a user authentication system"
        },
        "output": {"task_type": "", "result": {}, "error": None},
        "messages": []
    }
)

print(result)
```

---

## AWS AgentCore Deployment

AWS AgentCore allows deploying LangGraph agents to AWS infrastructure.

### Prerequisites

1. **AWS Account** with appropriate permissions
2. **AWS CLI** configured
3. **EKS Cluster** (if using Kubernetes)
4. **LangGraph Cloud** account (optional, for managed deployment)

### Deployment Options

#### Option 1: LangGraph Cloud → AWS

LangGraph Cloud can deploy directly to your AWS account:

```bash
# Login to LangGraph Cloud
langgraph cloud login

# Deploy to AWS
langgraph cloud deploy \
  --cloud-provider aws \
  --region us-east-1 \
  --config langgraph.json
```

#### Option 2: Manual EKS Deployment

1. **Build Docker Image**

```bash
# Use LangGraph's base image
FROM langchain/langgraph-api:latest

# Copy your application
COPY backend /app/backend
COPY langgraph.json /app/
COPY .env /app/

WORKDIR /app
```

2. **Push to ECR**

```bash
# Create ECR repository
aws ecr create-repository --repository-name dataforge-agent

# Build and push
docker build -t dataforge-agent .
docker tag dataforge-agent:latest \
  <account-id>.dkr.ecr.us-east-1.amazonaws.com/dataforge-agent:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/dataforge-agent:latest
```

3. **Deploy to EKS**

```bash
# Apply Kubernetes manifests (see infrastructure/k8s/)
kubectl apply -f infrastructure/k8s/namespace.yaml
kubectl apply -f infrastructure/k8s/secrets.yaml
kubectl apply -f infrastructure/k8s/configmap.yaml
kubectl apply -f infrastructure/k8s/backend-deployment.yaml
kubectl apply -f infrastructure/k8s/backend-service.yaml
kubectl apply -f infrastructure/k8s/ingress.yaml
```

#### Option 3: AWS Lambda (Serverless)

For serverless deployment, you can package the agent as a Lambda function:

```bash
# Install serverless dependencies
pip install aws-lambda-powertools

# Create Lambda deployment package
# (See AWS Lambda documentation for LangGraph deployment)
```

### Environment Variables for Production

Update your `.env` for production:

```bash
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=<use-iam-role-in-eks>
AWS_SECRET_ACCESS_KEY=<use-iam-role-in-eks>

# Bedrock Configuration
LLM_MODEL=anthropic.claude-3-5-haiku-20241022:0
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=4096

# LangSmith (Production)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=<prod-key>
LANGCHAIN_PROJECT=dataforge-studio-prod

# Redis (for production memory)
REDIS_URL=redis://dataforge-redis.default.svc.cluster.local:6379
USE_REDIS=true

# S3 Storage
S3_BUCKET=dataforge-artifacts-prod
USE_S3=true

# API Configuration
API_KEY=<secure-api-key>
```

---

## Troubleshooting

### Issue: "Module not found" when running agent

**Solution:**
- Ensure `backend` is in `dependencies` in `langgraph.json`
- Check that paths are relative to project root
- Verify Python path is set correctly in `agent.py`

### Issue: LangSmith traces not appearing

**Solution:**
- Check `LANGCHAIN_TRACING_V2=true` in `.env`
- Verify `LANGCHAIN_API_KEY` is correct
- Check network connectivity to `https://api.smith.langchain.com`

### Issue: AWS Bedrock throttling errors

**Solution:**
- Increase service quotas (see AWS quota guide)
- Add exponential backoff (already implemented in `tools.py`)
- Use longer delays between requests
- Consider caching LLM responses

### Issue: "Graph not found" in LangGraph

**Solution:**
- Ensure the graph is exported as `agent` in `agent.py`
- Verify the path in `langgraph.json` is correct
- Check that the graph is compiled (`.compile()`)

---

## Next Steps

1. **Test locally** with `langgraph dev`
2. **View traces** in LangSmith
3. **Build Docker image** for deployment
4. **Deploy to EKS** using provided Kubernetes manifests
5. **Set up monitoring** with CloudWatch and X-Ray
6. **Configure autoscaling** with HPA (Horizontal Pod Autoscaler)

## Resources

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LangSmith Documentation](https://docs.smith.langchain.com/)
- [AWS AgentCore Documentation](https://aws.amazon.com/bedrock/agents/)
- [LangGraph Cloud](https://langchain-ai.github.io/langgraph/cloud/)

