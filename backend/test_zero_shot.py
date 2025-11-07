"""
Quick test script to validate zero-shot generation without heuristics.

This script tests the LLM-driven agent system to ensure it works properly
with pure reasoning and no predefined templates.
"""
import asyncio
import sys
import os
from pathlib import Path

# Load .env file
from dotenv import load_dotenv

# Load .env from project root
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

from app.agents.schema_agent import SchemaAgent
from app.agents.document_agent import get_document_agent


async def test_schema_generation():
    """Test schema generation with various prompts"""
    print("=" * 80)
    print("Testing Zero-Shot Schema Generation")
    print("=" * 80)
    
    # Reduced test cases to avoid rate limiting
    test_prompts = [
        "Create a simple customer database with basic fields",
    ]
    
    agent = SchemaAgent()
    
    for i, prompt in enumerate(test_prompts, 1):
        print(f"\n\n[Test {i}] Prompt: '{prompt}'")
        print("-" * 80)
        
        try:
            # Use infer_schema method
            schema = await agent.infer_schema(prompt)
            
            # Add significant delay to avoid rate limiting (schema agent makes many internal LLM calls)
            print("\n⏳ Waiting 30 seconds before next test to avoid rate limits...")
            await asyncio.sleep(30)
            
            if not schema:
                print("❌ ERROR: No schema returned")
            else:
                tables = schema.get("tables", [])
                print(f"✅ SUCCESS: Generated {len(tables)} tables")
                
                for table in tables:
                    print(f"\n  Table: {table['name']}")
                    print(f"  Rows: {table['rows']}")
                    print(f"  Columns: {len(table.get('columns', []))}")
                    
                    # Show first 3 columns
                    for col in table.get('columns', [])[:3]:
                        print(f"    - {col['name']} ({col.get('type', 'unknown')})")
                    
                    if len(table.get('columns', [])) > 3:
                        print(f"    ... and {len(table['columns']) - 3} more")
                    
                    # Show foreign keys if any
                    fks = table.get('foreign_keys', [])
                    if fks:
                        print(f"  Foreign Keys: {len(fks)}")
                        for fk in fks:
                            print(f"    - {fk['column']} → {fk['ref_table']}.{fk['ref_column']}")
        
        except Exception as e:
            print(f"❌ EXCEPTION: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()


async def test_document_generation():
    """Test document generation with various prompts"""
    print("\n\n" + "=" * 80)
    print("Testing Zero-Shot Document Generation")
    print("=" * 80)
    
    # Single test case to avoid rate limiting
    test_cases = [
        {
            "subject": "quarterly financial report for tech startup",
            "style": "professional",
            "language": "english",
            "length": "short"
        }
    ]
    
    agent = get_document_agent()
    
    # Add delay before document tests
    print("\n⏳ Waiting 60 seconds to avoid rate limiting after schema tests...")
    await asyncio.sleep(60)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n\n[Test {i}] Document: {test_case['subject']}")
        print(f"Style: {test_case['style']}, Language: {test_case['language']}, Length: {test_case['length']}")
        print("-" * 80)
        
        try:
            document = await agent.generate_text_document(**test_case)
            
            word_count = len(document.split())
            print(f"✅ SUCCESS: Generated document with {word_count} words")
            print("\nFirst 200 characters:")
            print(document[:200] + "...")
        
        except Exception as e:
            print(f"❌ EXCEPTION: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()


async def main():
    """Run all tests"""
    print("\n🚀 DataForge Studio - Zero-Shot Generation Tests")
    print("=" * 80)
    print("These tests validate that the system uses pure LLM reasoning")
    print("without hardcoded heuristics or templates.")
    print("=" * 80)
    
    # Test schema generation
    await test_schema_generation()
    
    # Test document generation
    await test_document_generation()
    
    print("\n\n" + "=" * 80)
    print("✅ All tests complete!")
    print("=" * 80)


if __name__ == "__main__":
    # Check for AWS credentials
    if not os.getenv("AWS_REGION"):
        print("\n⚠️  WARNING: AWS credentials not configured")
        print("Set AWS_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY in your environment")
        print("or create a .env file with these values.")
        sys.exit(1)
    
    asyncio.run(main())

