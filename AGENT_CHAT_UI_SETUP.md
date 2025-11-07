# 🎨 Agent Chat UI - Complete Setup Guide

Based on official LangChain documentation, here's how to get the Chat UI running.

---

## ✅ What's Already Set Up

You now have **TWO agent graphs** configured in `langgraph.json`:

1. **`agent`** - Task-based agent (schema or document, structured input)
2. **`chat`** - Chat-compatible agent using MessagesState ⭐ **New!**

---

## 🚀 Quick Start: LangGraph Studio Chat Mode

**This is the EASIEST option** - it's built into LangGraph Studio!

### 1. Configure LangSmith (Optional but Recommended)

```bash
# Run the setup script
./setup_langsmith.sh

# Or manually add to .env:
echo "LANGCHAIN_TRACING_V2=true" >> .env
echo "LANGCHAIN_API_KEY=your_key_from_smith.langchain.com" >> .env
echo "LANGCHAIN_PROJECT=dataforge-studio" >> .env
```

### 2. Start LangGraph Studio

```bash
cd /Users/romainboluda/Documents/PersonalProjects/dataforge-studio
langgraph studio
```

**This will:**
- Start the agent server
- Open Studio in your browser automatically
- URL: http://localhost:8000 or https://smith.langchain.com/studio/

### 3. Switch to Chat Mode

Once Studio opens:

1. **Select the `chat` graph** from the dropdown (top of page)
2. **Click "Chat" mode** button (top right, next to "Graph")
3. **Start chatting!**

### 4. Try These Prompts

```
Create a simple e-commerce database with customers, orders, and products
```

```
Generate a professional technical specification document
```

```
Build a healthcare patient management schema with appointments
```

**Features:**
- ✅ Real-time chat interface
- ✅ Message history
- ✅ Tool visualization
- ✅ State inspection
- ✅ Time-travel debugging
- ✅ LangSmith trace links

---

## 🎨 Alternative: Standalone Agent Chat UI (Next.js)

If you want a fully customizable, standalone chat interface, you can use the open-source Agent Chat UI.

### Prerequisites

- Node.js 18+ installed
- Your LangGraph agent running (`langgraph dev`)

### Option A: Use NPX (Quickest)

```bash
# Start your agent first
cd /Users/romainboluda/Documents/PersonalProjects/dataforge-studio
langgraph dev &

# In a new terminal, run the Chat UI
npx agent-chat-ui --url http://localhost:8123 --graph chat
```

### Option B: Clone and Customize

```bash
# Clone the Agent Chat UI repository
git clone https://github.com/langchain-ai/agent-chat-ui.git
cd agent-chat-ui

# Install dependencies
npm install

# Configure your agent URL
echo "NEXT_PUBLIC_AGENT_URL=http://localhost:8123" > .env.local
echo "NEXT_PUBLIC_GRAPH_ID=chat" >> .env.local

# Run the development server
npm run dev
```

**Then open:** http://localhost:3000

### Customize the UI

The Agent Chat UI is built with Next.js and fully customizable:

```bash
agent-chat-ui/
├── app/
│   ├── page.tsx           # Main chat interface
│   └── components/
│       ├── Chat.tsx       # Chat component
│       ├── Message.tsx    # Message bubbles
│       └── ToolCall.tsx   # Tool visualization
├── styles/
│   └── globals.css        # Styling
└── public/
    └── logo.svg           # Your logo
```

**Customization examples:**
- Change theme colors in `styles/globals.css`
- Add your logo in `public/`
- Modify message display in `components/Message.tsx`
- Add custom tool visualizations in `components/ToolCall.tsx`

---

## 📊 Comparing the Options

| Feature | Studio Chat Mode | Agent Chat UI (Next.js) |
|---------|------------------|-------------------------|
| **Setup Time** | < 1 minute | 5-10 minutes |
| **Installation** | Built-in | Separate clone/npm |
| **Customization** | Limited | Fully customizable |
| **Graph Visualization** | ✅ Yes | ❌ No |
| **State Inspection** | ✅ Yes | ❌ No |
| **Time Travel Debug** | ✅ Yes | ❌ No |
| **Production Ready** | ✅ Yes | ✅ Yes |
| **Branding** | LangChain | Your own |
| **Best For** | Development & Testing | Production deployment |

---

## 🎯 Recommended Workflow

### For Development (Recommended)

```bash
# Use LangGraph Studio
langgraph studio

# Select "chat" graph
# Switch to "Chat" mode
# Start testing!
```

**Advantages:**
- Instant setup
- Full debugging features
- LangSmith integration
- No additional dependencies

### For Production

```bash
# Deploy agent to LangSmith or AWS
# Clone and customize Agent Chat UI
# Deploy Next.js app to Vercel/Netlify
# Point UI to your agent endpoint
```

---

## 🧪 Testing Your Chat Agent

### Test Locally

```bash
# Test the chat agent directly
conda activate dataforge-studio
python backend/src/chat_agent.py
```

### Test with Studio

```bash
langgraph studio
# Select "chat" graph
# Use Chat mode
```

### Test with API

```bash
# Start dev server
langgraph dev

# Send a message
curl -X POST http://localhost:8123/runs/stream \
  -H "Content-Type: application/json" \
  -d '{
    "assistant_id": "chat",
    "input": {
      "messages": [{
        "role": "user",
        "content": "Create a user database"
      }]
    }
  }'
```

---

## 🛠️ Troubleshooting

### Issue: "Chat mode not available"

**Solution:**
- Ensure your graph uses `MessagesState` (✅ the `chat` graph already does)
- Check that you've selected the `chat` graph, not `agent`

### Issue: Studio not opening

**Solution:**
```bash
# Try with verbose logging
langgraph studio --verbose

# Or specify port
langgraph studio --port 8080
```

### Issue: Agent not responding

**Solution:**
1. Test agent directly: `python backend/src/chat_agent.py`
2. Check AWS credentials: `python backend/check_bedrock.py`
3. View LangSmith traces for errors
4. Verify `.env` is loaded

### Issue: "Module not found" errors

**Solution:**
```bash
# Reinstall dependencies
conda activate dataforge-studio
pip install --upgrade langgraph langgraph-cli langserve
```

---

## 📚 Additional Resources

- **Official Docs**: https://docs.langchain.com/langsmith/studio
- **Agent Chat UI Repo**: https://github.com/langchain-ai/agent-chat-ui
- **LangGraph Docs**: https://langchain-ai.github.io/langgraph/
- **Studio Tutorial**: https://docs.langchain.com/langsmith/use-studio

---

## 🎉 You're All Set!

**Quick Command:**

```bash
# Start chatting NOW:
langgraph studio
```

1. Select **`chat`** graph
2. Click **"Chat"** mode
3. Type: "Create an e-commerce database"
4. Watch the agent work! 🚀

---

## Next Steps

1. ✅ Start Studio and try Chat mode
2. 📊 Configure LangSmith for traces
3. 🧪 Test different prompts
4. 🎨 (Optional) Clone Agent Chat UI for customization
5. 🚀 Deploy to production

See `CHAT_UI_QUICKSTART.md` for even more details!

