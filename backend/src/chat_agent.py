"""
Chat-Compatible Agent for LangGraph Studio Chat Mode

This agent uses MessagesState for compatibility with Studio's Chat Mode.
It provides a conversational interface for schema and document generation.

Uses a ReAct agent that intelligently selects between schema and document tools.
"""

from __future__ import annotations
from pathlib import Path
import sys

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.agents.schema_agent import SchemaAgent
from app.agents.document_agent import DocumentAgent
from app.core.config import settings
from app.services.generation.structured import StructuredDataGenerator
from langchain_aws import ChatBedrock
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.prebuilt import create_react_agent
from typing import Dict, Any
import json
import uuid
from pathlib import Path


# Initialize sub-agents and services
schema_agent_instance = SchemaAgent()
document_agent_instance = DocumentAgent()
data_generator = StructuredDataGenerator()


# Define tools for the agent to choose from
@tool
async def generate_database_schema(prompt: str) -> str:
    """
    Generate a synthetic database schema with tables, columns, and relationships.
    
    Use this tool when the user wants:
    - Database schemas, tables, or data models
    - Structured datasets (CSV, JSON, Excel)
    - Customer data, user data, product catalogs, etc.
    - Sample/test/mock data with specific fields
    - Multi-table databases with relationships
    
    Args:
        prompt: Description of the database/data structure needed
        
    Returns:
        A response containing the schema summary AND the full schema JSON 
        (which can be passed to generate_synthetic_data_files)
    """
    try:
        schema = await schema_agent_instance.infer_schema(prompt)
        if not schema:
            return "❌ Failed to generate schema"
        
        # Return formatted summary
        tables = schema.get("tables", [])
        result = f"✅ Generated database schema with {len(tables)} table(s):\n\n"
        
        for table in tables:
            result += f"**{table['name']}**\n"
            result += f"  - Rows: {table.get('rows', 0)}\n"
            result += f"  - Columns: {len(table.get('columns', []))}\n"
            
            # Show column names
            col_names = [col['name'] for col in table.get('columns', [])[:10]]
            result += f"  - Fields: {', '.join(col_names)}"
            if len(table.get('columns', [])) > 10:
                result += f" (+{len(table['columns']) - 10} more)"
            result += "\n\n"
        
        # Include full schema JSON (IMPORTANT: this can be passed to generate_synthetic_data_files)
        result += f"\n---\n**SCHEMA_JSON_START**\n```json\n{json.dumps(schema, indent=2)}\n```\n**SCHEMA_JSON_END**\n---"
        
        return result
    except Exception as e:
        return f"❌ Error generating schema: {str(e)}"


@tool
async def generate_synthetic_data_files(schema_text: str) -> str:
    """
    Generate actual CSV files with synthetic data from a schema.
    
    Use this tool AFTER generate_database_schema when the user wants to:
    - See the actual data (not just the schema structure)
    - Download CSV files with the generated data
    - View sample rows from the tables
    - Get the data for analysis or testing
    
    Args:
        schema_text: The output from generate_database_schema (contains schema JSON)
        
    Returns:
        Summary of generated files with sample data preview
    """
    try:
        # Extract schema JSON from the text
        if "SCHEMA_JSON_START" in schema_text and "SCHEMA_JSON_END" in schema_text:
            start_marker = "SCHEMA_JSON_START"
            end_marker = "SCHEMA_JSON_END"
            start_idx = schema_text.index(start_marker) + len(start_marker)
            end_idx = schema_text.index(end_marker)
            json_text = schema_text[start_idx:end_idx]
            # Remove markdown code fence if present
            json_text = json_text.replace("```json", "").replace("```", "").strip()
            schema = json.loads(json_text)
        else:
            # Try parsing as direct JSON
            schema = json.loads(schema_text)
        
        # Generate unique job ID
        job_id = str(uuid.uuid4())
        
        # Generate data files
        summary = await data_generator.generate_from_schema(job_id, schema)
        
        # Get job directory
        job_dir = Path(settings.LOCAL_ARTIFACTS_DIR) / job_id
        
        # Build response with file info and sample data
        result = f"✅ Generated synthetic data files!\n\n"
        result += f"📁 **Output Directory**: `{job_dir}`\n"
        result += f"📊 **Total Tables**: {len(summary['tables'])}\n"
        result += f"📈 **Total Rows**: {summary['total_rows']:,}\n\n"
        
        result += "### Generated Files:\n\n"
        
        for table_info in summary['tables']:
            table_name = table_info['name']
            csv_path = job_dir / f"{table_name}.csv"
            
            result += f"**{table_name}.csv**\n"
            result += f"  - Rows: {table_info['rows']:,}\n"
            result += f"  - Columns: {table_info['columns']}\n"
            result += f"  - Path: `{csv_path}`\n"
            
            # Show sample data (first 3 rows)
            if csv_path.exists():
                import pandas as pd
                df = pd.read_csv(csv_path)
                
                result += f"\n  Sample data (first 3 rows):\n"
                result += f"```\n{df.head(3).to_string(index=False)}\n```\n\n"
        
        result += f"\n💡 **Tip**: You can find all files in: `{job_dir}`"
        
        return result
        
    except Exception as e:
        import traceback
        return f"❌ Error generating data files: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"


@tool
async def generate_text_document(subject: str, style: str = "professional", length: str = "medium") -> str:
    """
    Generate a text document on any subject using an LLM.
    
    Use this tool when the user wants:
    - Written documents, reports, or articles
    - Guides, tutorials, or documentation
    - Business documents (proposals, memos, letters)
    - Creative writing (essays, stories)
    
    Do NOT use for structured data or databases - use generate_database_schema instead.
    
    Args:
        subject: What the document should be about
        style: Writing style (professional, casual, technical, creative)
        length: Document length (short, medium, long)
        
    Returns:
        The generated text document
    """
    try:
        document = await document_agent_instance.generate_text_document(
            subject=subject,
            style=style,
            language="english",
            length=length
        )
        
        if not document:
            return "❌ Failed to generate document"
        
        word_count = len(document.split())
        result = f"✅ Generated {length} document ({word_count} words):\n\n"
        result += "---\n\n"
        result += document[:2000]  # Show first 2000 chars
        
        if len(document) > 2000:
            result += f"\n\n... (truncated, full document has {word_count} words)"
        
        return result
    except Exception as e:
        return f"❌ Error generating document: {str(e)}"


# Create LLM for the orchestrator agent
def get_orchestrator_llm():
    return ChatBedrock(
        model_id=settings.LLM_MODEL,
        region_name=settings.AWS_REGION,
        provider="anthropic",
        model_kwargs={
            "temperature": 0.3,  # Lower temp for more consistent tool selection
            "max_tokens": 4096,
        },
    )


# System prompt for the orchestrator agent
SYSTEM_PROMPT = """You are DataForge Studio, an AI assistant that helps users generate synthetic data and documents.

You have three main capabilities:

1. **generate_database_schema**: Create the structure/schema for databases and tables
2. **generate_synthetic_data_files**: Generate actual CSV files with synthetic data from a schema
3. **generate_text_document**: Write documents, reports, guides, and other text content

WORKFLOW FOR DATA GENERATION:
- If user asks for "data" or "dataset", FIRST call generate_database_schema to create the structure
- Then, if they want to see/download the actual data, call generate_synthetic_data_files with the schema
- The schema from step 1 should be passed as schema_json to step 2

For documents/reports, use generate_text_document.

Be concise and helpful. After generating a schema, ask if they want to generate the actual data files."""


# Create the ReAct agent
agent = create_react_agent(
    model=get_orchestrator_llm(),
    tools=[generate_database_schema, generate_synthetic_data_files, generate_text_document],
    prompt=SYSTEM_PROMPT,
)


# For direct testing
if __name__ == "__main__":
    import asyncio
    
    async def test():
        """Test the chat agent locally"""
        print("\n🧪 Testing DataForge Chat Agent (ReAct-based)")
        print("=" * 70)
        
        # Test 1: Schema generation
        print("\n📊 Test 1: Generate customer dataset")
        result1 = await agent.ainvoke({
            "messages": [
                HumanMessage(content="Generate a dataset of customer data")
            ]
        })
        
        print("\nAgent Response:")
        for msg in result1["messages"]:
            if isinstance(msg, AIMessage) and not msg.tool_calls:
                print(f"\n{msg.content[:500]}...")
        
        # Test 2: Document generation
        print("\n\n📝 Test 2: Generate a report")
        result2 = await agent.ainvoke({
            "messages": [
                HumanMessage(content="Write a report about synthetic data benefits")
            ]
        })
        
        print("\nAgent Response:")
        for msg in result2["messages"]:
            if isinstance(msg, AIMessage) and not msg.tool_calls:
                print(f"\n{msg.content[:500]}...")
        
        print("\n" + "=" * 70)
        print("✅ Tests complete!")
    
    asyncio.run(test())

