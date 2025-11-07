# ✅ Corrected: How to Access LangGraph Studio

## The Right Way to Access Studio

**Studio is NOT a CLI command** - it's a web-based IDE hosted by LangSmith!

---

## 🚀 Quick Start (2 Steps)

### Step 1: Start Your Local Agent Server

```bash
cd /Users/romainboluda/Documents/PersonalProjects/dataforge-studio
conda activate dataforge-studio
langgraph dev
```

**This starts:**
- Local agent server on `http://localhost:2024`
- Prints Studio URL in the output

**Output will look like:**
```
> - 🚀 API: http://127.0.0.1:2024
> - 🎨 Studio UI: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024
> - 📚 API Docs: http://127.0.0.1:2024/docs
```

### Step 2: Open Studio in Browser

**Option A: Click the Link**
- Look for the `Studio UI:` line in the terminal output
- Click the URL or copy it to your browser

**Option B: Navigate Manually**
1. Go to https://smith.langchain.com/
2. Sign in (or create free account)
3. Click **"Studio"** in the sidebar
4. Connect to `http://localhost:2024`

---

## 📊 Using Studio

Once Studio loads:

### 1. Select Your Graph
- Use the dropdown at the top
- Choose either:
  - **`agent`** - Task-based agent
  - **`chat`** - Chat-compatible agent

### 2. Choose Mode
- **Graph mode** - Full visualization with nodes and edges
- **Chat mode** - Simple chat interface (only for `chat` graph)

### 3. Start Testing!
- Type prompts in the input area
- Watch execution in real-time
- Inspect state at each step
- Debug with time-travel

---

## 🎨 Alternative: Use Built-in Playground

If you don't want to use LangSmith Studio, use the built-in API playground:

```bash
langgraph dev
```

Then open: **http://localhost:2024/docs**

This provides:
- API documentation
- Interactive request builder
- No LangSmith account needed

---

## 🔧 Troubleshooting

### Issue: "Cannot connect to agent"

**Solution:**
```bash
# Make sure dev server is running
langgraph dev

# Check if port 2024 is in use
lsof -i :2024

# Try a different port
langgraph dev --port 8080
```

### Issue: "Studio won't load"

**Solution:**
1. Check that `langgraph dev` is running
2. Verify you're signed into smith.langchain.com
3. Make sure firewall allows localhost connections
4. Try the direct URL from terminal output

### Issue: "Graph not found"

**Solution:**
1. Check your `langgraph.json` file exists
2. Verify the graph paths are correct
3. Restart `langgraph dev`

---

## 📚 Three Ways to Test Your Agent

### 1. LangSmith Studio (Visual IDE)
```bash
langgraph dev
# Then open: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024
```
**Best for:** Visual debugging, graph inspection, development

### 2. API Playground (Built-in)
```bash
langgraph dev
# Then open: http://localhost:2024/docs
```
**Best for:** API testing, no account needed

### 3. Direct Python Test
```bash
conda activate dataforge-studio
python backend/src/chat_agent.py
```
**Best for:** Quick validation, debugging

---

## 🎯 Corrected Workflow

```bash
# 1. Activate environment
conda activate dataforge-studio

# 2. Start dev server (NOT "langgraph studio")
langgraph dev

# 3. Open Studio from the URL in terminal output
# OR use the built-in playground at http://localhost:2024/docs

# 4. Start testing!
```

---

## 💡 Why No "langgraph studio" Command?

Studio is a **cloud-hosted IDE** that connects to your local agent server. It's not a separate CLI command but a web application provided by LangSmith.

Think of it like:
- `langgraph dev` = Your local backend server
- Studio = Frontend IDE in your browser
- They communicate over HTTP

---

## 🚀 Try It Now!

```bash
# Start your agent server
langgraph dev
```

**Then:**
1. Copy the Studio URL from terminal
2. Open in browser
3. Sign in to LangSmith (free)
4. Select your graph
5. Start chatting!

---

See `AGENT_CHAT_UI_SETUP.md` for additional chat UI options!

