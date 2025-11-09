"""Agent tools for LangChain/LangGraph agents
- Pure LLM reasoning, no heuristics
- Uses ChatBedrockConverse for streaming
"""

from typing import Dict, Any, List
import logging
from langchain_core.tools import tool
from langchain_aws import ChatBedrockConverse  # New Converse API
from langchain_core.messages import HumanMessage, SystemMessage
import json
import asyncio
import random

from app.core.config import settings

logger = logging.getLogger(__name__)


async def llm_with_retry(llm, messages, max_retries=5, base_delay=2):
    """
    Invoke LLM with exponential backoff retry logic for throttling errors.

    Args:
        llm: LLM instance
        messages: Messages to send
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds (will be exponentially increased)

    Returns:
        LLM response

    Raises:
        Exception if all retries are exhausted
    """
    for attempt in range(max_retries):
        try:
            return await llm.ainvoke(messages)
        except Exception as e:
            # Check if it's a throttling error
            is_throttling = (
                "ThrottlingException" in str(type(e))
                or "Too many requests" in str(e)
                or "throttl" in str(e).lower()
            )

            if not is_throttling or attempt == max_retries - 1:
                # Not a throttling error or last attempt - raise it
                raise

            # Calculate exponential backoff with jitter
            delay = base_delay * (2**attempt) + random.uniform(0, 1)
            print(
                f"⚠️  Rate limited, retrying in {delay:.1f}s (attempt {attempt + 1}/{max_retries})..."
            )
            await asyncio.sleep(delay)

    raise Exception("Max retries exceeded")


def get_llm():
    """Get LLM instance for tool reasoning with ChatBedrockConverse"""
    return ChatBedrockConverse(
        model=settings.LLM_MODEL,  # 'model' not 'model_id'
        region_name=settings.AWS_REGION,
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=settings.LLM_MAX_TOKENS,
    )


@tool
async def analyze_prompt(prompt: str) -> Dict[str, Any]:
    """
    Use LLM reasoning to analyze a natural language prompt and extract entities,
    relationships, and constraints.

    The LLM uses its knowledge to identify tables, relationships, and domain context.
    No heuristics - pure reasoning based on LLM's understanding of data modeling.

    Args:
        prompt: Natural language description of desired data

    Returns:
        Dictionary with extracted entities, relationships, constraints, and domain
    """
    llm = get_llm()

    analysis_prompt = f"""You are a data modeling expert. Analyze this data generation request and extract:

1. ENTITIES: What tables/entities are needed? Think about the business domain.
2. RELATIONSHIPS: How do these entities relate to each other? (one-to-many, many-to-many, etc.)
3. DOMAIN: What business domain is this? (e.g., ecommerce, healthcare, finance, marketing)
4. ROW ESTIMATES: Default to 100 rows per table unless the user specifically requests more. Use reasonable small numbers (100-1000) for typical datasets.

Request: "{prompt}"

Reason through this step-by-step, considering typical data modeling patterns.

Return ONLY a JSON object with this exact structure:
{{
    "entities": ["entity1", "entity2"],
    "relationships": [
        {{"from": "entity1", "to": "entity2", "type": "many_to_one", "foreign_key": "entity2_id"}}
    ],
    "domain": "domain_name",
    "size_hints": {{"entity1": 100, "entity2": 100}},
    "reasoning": "Brief explanation of your analysis"
}}"""

    messages = [
        SystemMessage(content="You are a data modeling expert who reasons about database schemas."),
        HumanMessage(content=analysis_prompt),
    ]

    response = await llm_with_retry(llm, messages)
    
    logger.info(f"🤖 LLM response type: {type(response)}")
    logger.info(f"🤖 LLM response.content type: {type(response.content)}")
    logger.info(f"🤖 LLM response.content: {response.content}")

    # Parse JSON response
    try:
        # Extract content (ChatBedrockConverse returns list of blocks, ChatBedrock returns string)
        content = response.content
        if isinstance(content, list):
            # ChatBedrockConverse format: list of content blocks
            # Handle different block types: text, reasoning, etc.
            text_parts = []
            for block in content:
                if isinstance(block, dict):
                    if "text" in block:
                        text_parts.append(block["text"])
                    # Skip reasoningContent blocks - we only want the actual response
                elif isinstance(block, str):
                    text_parts.append(block)
                else:
                    text_parts.append(str(block))
            content = " ".join(text_parts)
        
        logger.info(f"📝 Extracted content: {content[:200]}...")
        
        # Extract JSON from response (handle markdown code blocks)
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        logger.info(f"🔍 Parsing JSON content: {content[:200]}...")
        result = json.loads(content.strip())
        result["original_prompt"] = prompt
        logger.info(f"✅ Successfully parsed analysis: {result.get('entities')}")
        return result
    except json.JSONDecodeError as e:
        # Fallback: return minimal structure
        logger.error(f"❌ JSON parsing failed: {e}")
        logger.error(f"❌ Raw content that failed: {content[:500]}")
        return {
            "entities": ["data"],
            "relationships": [],
            "domain": "generic",
            "size_hints": {"data": 100},
            "reasoning": "Failed to parse LLM response",
            "original_prompt": prompt,
        }
    except Exception as e:
        logger.error(f"❌ Unexpected error in analyze_prompt: {e}", exc_info=True)
        return {
            "entities": ["data"],
            "relationships": [],
            "domain": "generic",
            "size_hints": {"data": 100},
            "reasoning": f"Error: {str(e)}",
            "original_prompt": prompt,
        }


@tool
async def suggest_columns(
    entity: str, domain: str = "generic", context: str = ""
) -> List[Dict[str, Any]]:
    """
    Use LLM reasoning to suggest appropriate columns for an entity.

    The LLM leverages its knowledge of typical data structures for different entity types
    and business domains. No hardcoded templates - pure reasoning.

    Args:
        entity: Entity/table name (e.g., "customers", "orders")
        domain: Business domain (e.g., "ecommerce", "finance", "healthcare")
        context: Additional context about the entity

    Returns:
        List of suggested columns with types and constraints
    """
    llm = get_llm()

    column_prompt = f"""You are a database schema expert. Design columns for this entity:

Entity: "{entity}"
Domain: "{domain}"
Context: "{context if context else 'Standard business application'}"

Consider:
1. Primary key (typically an ID field)
2. Core business data fields specific to this entity type
3. Common metadata (timestamps, status, etc.)
4. Appropriate data types and constraints
5. Fields that would typically relate to other entities (foreign keys)

Think about what makes sense for this entity in this domain. Use your knowledge of common data patterns.

Available data types:
- uuid: Unique identifier
- int: Integer numbers
- float: Decimal numbers
- string: Text data
- email: Email addresses
- date: Date only
- datetime: Date and time
- boolean: True/False
- categorical: Fixed set of values

Return ONLY a JSON array of column objects:
[
    {{
        "name": "column_name",
        "type": "data_type",
        "unique": true/false,
        "null_ratio": 0.0-1.0,
        "categories": ["val1", "val2"],  // only for categorical
        "description": "what this column represents"
    }}
]"""

    messages = [
        SystemMessage(
            content="You are a database schema expert who designs appropriate table structures."
        ),
        HumanMessage(content=column_prompt),
    ]

    response = await llm_with_retry(llm, messages)

    # Parse JSON response
    try:
        # Extract content (ChatBedrockConverse returns list of blocks)
        content = response.content
        if isinstance(content, list):
            # Extract only text blocks, skip reasoning blocks
            text_parts = []
            for block in content:
                if isinstance(block, dict) and "text" in block:
                    text_parts.append(block["text"])
                elif isinstance(block, str):
                    text_parts.append(block)
            content = " ".join(text_parts)
        
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        columns = json.loads(content.strip())
        logger.info(f"✅ Successfully suggested {len(columns)} columns for {entity}")
        return columns
    except json.JSONDecodeError as e:
        # Fallback: minimal structure
        logger.error(f"❌ JSON parsing failed for suggest_columns({entity}): {e}")
        logger.error(f"❌ Raw content: {content[:500] if 'content' in locals() else 'N/A'}")
        return [
            {"name": f"{entity.rstrip('s')}_id", "type": "uuid", "unique": True},
            {"name": "name", "type": "string"},
            {"name": "created_at", "type": "datetime"},
        ]


@tool
async def infer_relationships(tables: List[str], domain: str = "generic") -> List[Dict[str, str]]:
    """
    Use LLM reasoning to infer foreign key relationships between tables.

    The LLM reasons about which entities typically reference each other based on
    its knowledge of data modeling patterns and business logic.

    Args:
        tables: List of table names
        domain: Business domain for context

    Returns:
        List of inferred foreign key relationships
    """
    llm = get_llm()

    relationship_prompt = f"""You are a database design expert. Analyze these tables and determine logical relationships:

Tables: {', '.join(tables)}
Domain: {domain}

Think about:
1. Which entities typically reference others? (e.g., orders reference customers)
2. What foreign key relationships make business sense?
3. What is the cardinality? (one-to-many, many-to-many)

Use your knowledge of typical data models. Consider that:
- Child tables typically reference parent tables (orders → customers)
- Transaction-like entities reference core entities
- Join/linking tables connect many-to-many relationships

Return ONLY a JSON array:
[
    {{
        "parent_table": "parent_table_name",
        "child_table": "child_table_name",
        "foreign_key": "column_name_in_child",
        "reference_key": "column_name_in_parent",
        "cardinality": "many_to_one",
        "reasoning": "why this relationship exists"
    }}
]

If no relationships make sense, return an empty array []."""

    messages = [
        SystemMessage(
            content="You are a database design expert who understands entity relationships."
        ),
        HumanMessage(content=relationship_prompt),
    ]

    response = await llm_with_retry(llm, messages)

    # Parse JSON response
    try:
        # Extract content (ChatBedrockConverse returns list of blocks)
        content = response.content
        if isinstance(content, list):
            # Extract only text blocks, skip reasoning blocks
            text_parts = []
            for block in content:
                if isinstance(block, dict) and "text" in block:
                    text_parts.append(block["text"])
                elif isinstance(block, str):
                    text_parts.append(block)
            content = " ".join(text_parts)
        
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        relationships = json.loads(content.strip())
        return relationships if isinstance(relationships, list) else []
    except json.JSONDecodeError:
        return []


@tool
def validate_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate a data schema for correctness and completeness.

    Args:
        schema: Schema dictionary to validate

    Returns:
        Validation result with errors and warnings
    """
    errors = []
    warnings = []

    # Check required top-level fields
    if "tables" not in schema:
        errors.append("Schema must have a 'tables' field")
        return {"valid": False, "errors": errors, "warnings": warnings}

    tables = schema.get("tables", [])
    if not isinstance(tables, list):
        errors.append("'tables' must be a list")
        return {"valid": False, "errors": errors, "warnings": warnings}

    if len(tables) == 0:
        errors.append("Schema must have at least one table")
        return {"valid": False, "errors": errors, "warnings": warnings}

    table_names = set()

    for i, table in enumerate(tables):
        if not isinstance(table, dict):
            errors.append(f"Table {i} must be a dictionary")
            continue

        # Check required table fields
        if "name" not in table:
            errors.append(f"Table {i} missing 'name' field")
            continue

        name = table["name"]
        if name in table_names:
            errors.append(f"Duplicate table name: {name}")
        table_names.add(name)

        if "columns" not in table or not table["columns"]:
            errors.append(f"Table '{name}' must have at least one column")

        # Validate rows
        rows = table.get("rows", 0)
        if not isinstance(rows, int) or rows < 1:
            errors.append(f"Table '{name}' must have positive integer 'rows'")

        # Check columns
        columns = table.get("columns", [])
        if not isinstance(columns, list):
            errors.append(f"Table '{name}' columns must be a list")
            continue

        column_names = set()
        for j, col in enumerate(columns):
            if not isinstance(col, dict):
                errors.append(f"Table '{name}' column {j} must be a dictionary")
                continue

            if "name" not in col:
                errors.append(f"Table '{name}' column {j} missing 'name'")
                continue

            col_name = col["name"]
            if col_name in column_names:
                warnings.append(f"Table '{name}' has duplicate column: {col_name}")
            column_names.add(col_name)

            if "type" not in col:
                warnings.append(
                    f"Table '{name}' column '{col_name}' missing 'type', will default to 'string'"
                )

        # Validate primary key
        pk = table.get("primary_key")
        if pk and pk not in column_names:
            warnings.append(f"Table '{name}' primary key '{pk}' not in columns")

        # Validate foreign keys
        fks = table.get("foreign_keys", [])
        for fk in fks:
            if "column" not in fk or "ref_table" not in fk:
                errors.append(f"Table '{name}' has invalid foreign key definition")

    # Validate foreign key references
    for table in tables:
        fks = table.get("foreign_keys", [])
        for fk in fks:
            ref_table = fk.get("ref_table")
            if ref_table and ref_table not in table_names:
                errors.append(
                    f"Table '{table['name']}' references non-existent table '{ref_table}'"
                )

    return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}


@tool
def normalize_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize and clean a schema definition.

    Args:
        schema: Raw schema dictionary

    Returns:
        Normalized schema
    """
    normalized = {"tables": []}

    if "seed" in schema:
        normalized["seed"] = schema["seed"]

    for table in schema.get("tables", []):
        normalized_table = {
            "name": str(table.get("name", "unnamed")),
            "rows": int(table.get("rows", 100)),
            "columns": [],
        }

        # Normalize primary key
        if "primary_key" in table:
            pk = table["primary_key"]
            if isinstance(pk, list) and pk:
                normalized_table["primary_key"] = str(pk[0])
            elif isinstance(pk, str):
                normalized_table["primary_key"] = pk

        # Normalize columns
        for col in table.get("columns", []):
            if isinstance(col, dict) and "name" in col:
                normalized_col = {"name": str(col["name"]), "type": str(col.get("type", "string"))}
                # Copy optional fields
                for field in ["unique", "null_ratio", "categories", "range", "distribution"]:
                    if field in col:
                        normalized_col[field] = col[field]
                normalized_table["columns"].append(normalized_col)

        # Normalize foreign keys
        if "foreign_keys" in table:
            normalized_table["foreign_keys"] = table["foreign_keys"]

        normalized["tables"].append(normalized_table)

    return normalized
