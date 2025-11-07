"""
Chat Server with UI for DataForge Agents

Provides a simple chat interface for testing schema and document generation agents.
Built with LangServe for automatic UI generation.

Usage:
    conda activate dataforge-studio
    python backend/chat_server.py

Then open: http://localhost:8001/agent/playground
"""

from pathlib import Path
import sys

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the agent
from src.agent import agent

# Try to import langserve
try:
    from langserve import add_routes
    LANGSERVE_AVAILABLE = True
except ImportError:
    LANGSERVE_AVAILABLE = False
    print("⚠️  Warning: langserve not installed")
    print("   Install with: pip install 'langserve[all]'")
    print("   Continuing without chat UI...")

# Create FastAPI app
app = FastAPI(
    title="DataForge Chat API",
    version="1.0.0",
    description="""
    Chat interface for DataForge synthetic data agents.
    
    Supports:
    - Schema generation from natural language
    - Document generation with customizable style
    - Real-time streaming responses
    """,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint with links"""
    return {
        "message": "DataForge Chat Server",
        "version": "1.0.0",
        "endpoints": {
            "playground": "/agent/playground",
            "docs": "/docs",
            "agent_api": "/agent",
        },
        "agent_types": ["schema", "document"],
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "langserve": LANGSERVE_AVAILABLE}


# Add agent routes with LangServe if available
if LANGSERVE_AVAILABLE:
    add_routes(
        app,
        agent,
        path="/agent",
        enable_feedback_endpoint=True,  # Allow users to provide feedback
        enable_public_trace_link_endpoint=True,  # Link to LangSmith traces
        playground_type="default",  # Use default playground UI
    )
    
    print("\n✅ LangServe routes added successfully!")
    print("   Chat UI available at: http://localhost:8001/agent/playground")
else:
    @app.post("/agent")
    async def agent_fallback(input_data: dict):
        """Fallback endpoint if LangServe is not available"""
        try:
            result = await agent.ainvoke(input_data)
            return result
        except Exception as e:
            return {"error": str(e)}


if __name__ == "__main__":
    import uvicorn
    
    print("\n╔══════════════════════════════════════════════════════════════════╗")
    print("║     🚀 DataForge Chat Server                                     ║")
    print("╚══════════════════════════════════════════════════════════════════╝\n")
    
    if LANGSERVE_AVAILABLE:
        print("📊 Chat UI:      http://localhost:8001/agent/playground")
    else:
        print("⚠️  Chat UI:     Not available (install langserve)")
    
    print("📖 API Docs:     http://localhost:8001/docs")
    print("🔌 Agent API:    http://localhost:8001/agent")
    print("❤️  Health:      http://localhost:8001/health")
    
    print("\n📝 Example usage:")
    print('   curl -X POST http://localhost:8001/agent \\')
    print('     -H "Content-Type: application/json" \\')
    print('     -d \'{"input": {"input": {"task_type": "schema", "prompt": "Create a user database"}}}\'')
    
    if LANGSERVE_AVAILABLE:
        print("\n💡 For best experience, open the playground in your browser!")
    
    print("\n" + "─" * 70 + "\n")
    
    # Start server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        log_level="info",
    )

