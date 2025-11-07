# LangSmith & Agent Chat UI Setup

Complete guide to setting up LangSmith tracing and the LangGraph Studio Chat UI for testing your agents.

---

## Part 1: LangSmith Setup

### 1. Get Your LangSmith API Key

1. Go to [LangSmith](https://smith.langchain.com/)
2. Sign up or log in (free tier available)
3. Click on your profile → **Settings**
4. Navigate to **API Keys**
5. Click **Create API Key**
6. Copy the key (starts with `lsv2_pt_...`)

### 2. Add to Your `.env` File

Add these lines to your `.env` file:

```bash
# LangSmith Configuration (for agent tracing & evaluation)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_pt_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
LANGCHAIN_PROJECT=dataforge-studio
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
```

**Field explanations:**

- `LANGCHAIN_TRACING_V2=true` - Enables automatic tracing
- `LANGCHAIN_API_KEY` - Your API key from LangSmith
- `LANGCHAIN_PROJECT` - Project name (creates if doesn't exist)
- `LANGCHAIN_ENDPOINT` - LangSmith API endpoint (default)

### 3. Verify It's Working

Run your test again:

```bash
cd /Users/romainboluda/Documents/PersonalProjects/dataforge-studio/backend
conda activate dataforge-studio
python test_zero_shot.py
```

Then check LangSmith:

1. Go to <https://smith.langchain.com/>
2. Select your project: **dataforge-studio**
3. You should see traces appearing in real-time!

### 4. What You'll See in LangSmith

**Traces show:**

- ✅ Every LLM call (with prompts and responses)
- ✅ Token usage per call
- ✅ Latency per step
- ✅ Errors and retries
- ✅ Full agent execution flow
- ✅ Cost estimates

**Example trace:**

```
Schema Agent Run
├─ analyze_prompt (2.3s, 1,234 tokens)
├─ suggest_columns (1.8s, 987 tokens)
├─ infer_relationships (1.5s, 765 tokens)
├─ validate_schema (0.9s, 432 tokens)
└─ normalize_schema (0.7s, 321 tokens)

Total: 7.2s, 3,739 tokens, $0.005
```

---

## Part 2: Agent Chat UI (LangGraph Studio)

LangGraph Studio provides an interactive chat interface for testing your agents.

### Option A: LangGraph Studio Desktop (Recommended)

This is the easiest way to get the Chat UI.

#### 1. Install LangGraph CLI

```bash
# If not already installed
pip install langgraph-cli
```

#### 2. Start LangGraph Studio

```bash
cd /Users/romainboluda/Documents/PersonalProjects/dataforge-studio

# Make sure your .env is configured
# Then start Studio
langgraph studio
```

This will:

- Start a local server
- Open a browser window with the UI
- Load your agent from `langgraph.json`

**Default URL:** <http://localhost:8000>

#### 3. Using the Chat UI

Once Studio opens, you'll see:

1. **Graph View** (left sidebar)
   - Visual representation of your agent
   - Shows nodes and edges
   - Click to inspect each node

2. **Chat Interface** (center)
   - Type messages to test your agent
   - See real-time responses
   - View intermediate steps

3. **State Inspector** (right sidebar)
   - See agent state at each step
   - Inspect variables and outputs
   - Debug agent behavior

#### 4. Testing Your Agents

**For Schema Generation:**

```text
You: Create a simple e-commerce database with customers, orders, and products

Agent: [Shows schema generation steps]
- Analyzing prompt...
- Generating customer table...
- Generating orders table...
- Setting up relationships...
- Validating schema...

Result: [Shows generated schema JSON]
```

**For Document Generation:**

```text
You: Generate a professional quarterly financial report for a tech startup

Agent: [Shows document generation]
- Analyzing requirements...
- Generating document...

Result: [Shows generated document]
```

---

### Option B: LangGraph Dev Server (API-based UI)

This provides an API you can integrate with custom UIs.

#### 1. Start Dev Server

```bash
cd /Users/romainboluda/Documents/PersonalProjects/dataforge-studio
langgraph dev
```

**Default URL:** <http://localhost:8123>

#### 2. Access the Built-in Playground

Navigate to: <http://localhost:8123/playground>

This provides a simple UI for testing your agent via API.

#### 3. API Endpoints

The dev server exposes these endpoints:

```bash
# List available assistants
GET http://localhost:8123/assistants

# Create a run
POST http://localhost:8123/runs/stream
{
  "assistant_id": "agent",
  "input": {
    "input": {
      "task_type": "schema",
      "prompt": "Create a user database"
    },
    "output": {"task_type": "", "result": {}, "error": null},
    "messages": []
  }
}

# Get run status
GET http://localhost:8123/runs/{run_id}
```

---

### Option C: Custom Chat UI with LangServe

For a production-ready chat UI, integrate with LangServe.

#### 1. Install LangServe

```bash
conda activate dataforge-studio
pip install "langserve[all]"
```

#### 2. Create Chat Server

Create `backend/chat_server.py`:

```python
"""Chat server with UI for DataForge agents"""
from fastapi import FastAPI
from langserve import add_routes
from backend.src.agent import agent

app = FastAPI(
    title="DataForge Chat API",
    version="1.0",
    description="Chat interface for DataForge agents"
)

# Add agent routes with built-in UI
add_routes(
    app,
    agent,
    path="/agent",
    enable_feedback_endpoint=True,
    enable_public_trace_link_endpoint=True,
    playground_type="default"  # or "chat" for chat-specific UI
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
```

#### 3. Run Chat Server

```bash
cd /Users/romainboluda/Documents/PersonalProjects/dataforge-studio
conda activate dataforge-studio
python backend/chat_server.py
```

#### 4. Access Chat UI

Navigate to: <http://localhost:8001/agent/playground>

This provides:

- Interactive chat interface
- Request/response inspection
- OpenAPI documentation
- Feedback collection

---

## Part 3: Advanced Configuration

### Customizing the Chat UI

You can customize the agent for better chat experience:

#### 1. Add Conversational Memory

Update `backend/src/agent.py` to include message history:

```python
class UnifiedAgentState(TypedDict):
    """State for the unified agent"""
    input: AgentInput
    output: AgentOutput
    messages: List[Any]  # This stores conversation history
    
    # Add memory
    conversation_history: List[Dict[str, str]]
```

#### 2. Add Streaming Responses

Enable streaming for real-time feedback:

```python
# In your agent nodes, use yield for streaming
async def handle_schema(state: UnifiedAgentState):
    yield {"messages": [{"role": "assistant", "content": "Starting schema analysis..."}]}
    
    result = await schema_agent.infer_schema(state["input"]["prompt"])
    
    yield {"messages": [{"role": "assistant", "content": "Schema generated!"}]}
    yield {"output": {"result": result}}
```

#### 3. Add Custom Prompts for Chat

Create chat-specific prompts in `backend/app/agents/chat_prompts.py`:

```python
CHAT_SYSTEM_PROMPT = """You are DataForge, an AI assistant specialized in:
- Generating synthetic data schemas
- Creating realistic documents
- Explaining data modeling concepts

Be concise, helpful, and technical when needed."""

CLARIFICATION_PROMPTS = {
    "schema": "What kind of database are you looking to create? (e.g., e-commerce, healthcare, finance)",
    "document": "What type of document do you need? (e.g., invoice, report, contract)"
}
```

---

## Part 4: Monitoring & Debugging

### Using LangSmith with Chat UI

When both are configured, you get powerful debugging:

1. **Run agent in Chat UI**
2. **See trace link** in UI (if enabled)
3. **Click trace link** → Opens LangSmith
4. **Inspect full execution** with prompts, outputs, timing

### Common Issues & Solutions

#### Issue: Chat UI not loading

**Solution:**

```bash
# Check if server is running
curl http://localhost:8000/health

# Check logs
langgraph studio --verbose

# Restart with clean state
langgraph studio --reset
```

#### Issue: Agent not responding in UI

**Solution:**

1. Check `.env` is loaded
2. Verify AWS credentials
3. Check LangSmith traces for errors
4. Test agent directly first: `python backend/src/agent.py`

#### Issue: Traces not appearing in LangSmith

**Solution:**

```bash
# Verify env vars are set
echo $LANGCHAIN_TRACING_V2
echo $LANGCHAIN_API_KEY

# Test connection
curl https://api.smith.langchain.com/info

# Reload .env
source .env  # or restart your terminal
```

---

## Part 5: Production Deployment

### Deploying Chat UI to Production

#### Option 1: LangGraph Cloud

Deploy your agent with built-in UI:

```bash
langgraph cloud login
langgraph cloud deploy \
  --name dataforge-studio \
  --config langgraph.json
```

This provides:

- Hosted agent endpoint
- Built-in chat UI
- Automatic scaling
- LangSmith integration

#### Option 2: Self-Hosted on AWS

Deploy using your existing EKS setup:

1. **Build Docker image** with LangServe
2. **Deploy to EKS** using K8s manifests
3. **Expose via Ingress** (already configured)
4. **Add CloudFront** for CDN

See `infrastructure/k8s/README.md` for deployment details.

---

## Quick Start Commands

```bash
# 1. Configure LangSmith in .env
echo "LANGCHAIN_TRACING_V2=true" >> .env
echo "LANGCHAIN_API_KEY=your_key_here" >> .env
echo "LANGCHAIN_PROJECT=dataforge-studio" >> .env

# 2. Start LangGraph Studio (Chat UI)
langgraph studio

# 3. Test your agent
# Open browser to http://localhost:8000
# Type: "Create a customer database"

# 4. View traces in LangSmith
# Open: https://smith.langchain.com/
```

---

## Resources

- [LangGraph Studio Docs](https://langchain-ai.github.io/langgraph/cloud/studio/)
- [LangSmith Documentation](https://docs.smith.langchain.com/)
- [LangServe Chat UI](https://github.com/langchain-ai/langserve)
- [LangGraph Cloud](https://langchain-ai.github.io/langgraph/cloud/)

---

## Next Steps

1. ✅ Configure LangSmith in `.env`
2. ✅ Run `langgraph studio`
3. ✅ Test agents in Chat UI
4. ✅ View traces in LangSmith
5. 📊 Evaluate agent performance
6. 🚀 Deploy to production
