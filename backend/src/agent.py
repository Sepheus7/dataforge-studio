"""
LangGraph Agent Entry Point for DataForge Studio

This module exports the main agent graph for LangGraph deployment.
Compatible with LangGraph Cloud, LangSmith, and AWS AgentCore.
"""

from __future__ import annotations
from pathlib import Path
import sys

# Add backend to path for imports
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.agents.schema_agent import SchemaAgent
from app.agents.document_agent import DocumentAgent
from langgraph.graph import StateGraph, END
from typing_extensions import TypedDict
from typing import Literal, Dict, Any, List, Optional, Union


class AgentInput(TypedDict):
    """Input schema for the unified agent"""
    task_type: Literal["schema", "document"]
    prompt: str
    # Document-specific fields
    style: Optional[str]
    language: Optional[str]
    length: Optional[str]
    document_type: Optional[str]
    context: Optional[Dict[str, Any]]


class AgentOutput(TypedDict):
    """Output schema for the unified agent"""
    task_type: str
    result: Union[Dict[str, Any], str]
    error: Optional[str]


class UnifiedAgentState(TypedDict):
    """State for the unified agent"""
    input: AgentInput
    output: AgentOutput
    messages: List[Any]


# Initialize sub-agents
schema_agent = SchemaAgent()
document_agent = DocumentAgent()


async def route_task(state: UnifiedAgentState) -> str:
    """Route to the appropriate agent based on task type"""
    task_type = state["input"]["task_type"]
    return task_type


async def handle_schema(state: UnifiedAgentState) -> UnifiedAgentState:
    """Handle schema generation tasks"""
    try:
        prompt = state["input"]["prompt"]
        result = await schema_agent.infer_schema(prompt)
        
        state["output"] = {
            "task_type": "schema",
            "result": result,
            "error": None,
        }
    except Exception as e:
        state["output"] = {
            "task_type": "schema",
            "result": {},
            "error": str(e),
        }
    
    return state


async def handle_document(state: UnifiedAgentState) -> UnifiedAgentState:
    """Handle document generation tasks"""
    try:
        input_data = state["input"]
        
        # Check if structured or text document
        if input_data.get("document_type"):
            result = await document_agent.generate_structured_document(
                document_type=input_data["document_type"],
                context=input_data.get("context", {}),
                language=input_data.get("language", "english"),
            )
        else:
            result = await document_agent.generate_text_document(
                subject=input_data["prompt"],
                style=input_data.get("style", "professional"),
                language=input_data.get("language", "english"),
                length=input_data.get("length", "medium"),
            )
        
        state["output"] = {
            "task_type": "document",
            "result": result,
            "error": None,
        }
    except Exception as e:
        state["output"] = {
            "task_type": "document",
            "result": "",
            "error": str(e),
        }
    
    return state


# Build the unified agent graph
def build_agent() -> StateGraph:
    """Build the unified agent graph for LangGraph deployment"""
    workflow = StateGraph(UnifiedAgentState)
    
    # Add nodes
    workflow.add_node("schema", handle_schema)
    workflow.add_node("document", handle_document)
    
    # Define routing
    workflow.set_conditional_entry_point(
        route_task,
        {
            "schema": "schema",
            "document": "document",
        }
    )
    
    # Both end after processing
    workflow.add_edge("schema", END)
    workflow.add_edge("document", END)
    
    return workflow.compile()


# Export the compiled agent graph for LangGraph
agent = build_agent()


# For direct testing
if __name__ == "__main__":
    import asyncio
    
    async def test():
        """Test the agent locally"""
        # Test schema generation
        result = await agent.ainvoke({
            "input": {
                "task_type": "schema",
                "prompt": "Create a simple user database",
            },
            "output": {"task_type": "", "result": {}, "error": None},
            "messages": [],
        })
        
        print("Schema Generation Result:")
        print(result["output"])
    
    asyncio.run(test())

