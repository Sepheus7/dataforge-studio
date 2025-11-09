"""Tests for LangChain/LangGraph agents"""

import pytest
from app.agents.schema_agent import get_schema_agent
from app.agents.tools import (
    analyze_prompt,
    suggest_columns,
    infer_relationships,
    validate_schema,
    normalize_schema,
)


class TestSchemaAgent:
    """Test Schema Agent functionality"""

    @pytest.mark.asyncio
    @pytest.mark.slow
    @pytest.mark.llm
    async def test_infer_schema_from_prompt(self, sample_prompt):
        """Test schema inference from natural language"""
        agent = get_schema_agent()

        schema = await agent.infer_schema(
            prompt=sample_prompt, size_hint={"customers": 100, "orders": 500}, seed=42
        )

        assert schema is not None
        assert "tables" in schema
        assert len(schema["tables"]) > 0
        assert schema.get("seed") == 42

    @pytest.mark.asyncio
    @pytest.mark.slow
    @pytest.mark.llm
    async def test_schema_agent_with_seed(self, sample_prompt):
        """Test deterministic schema generation with seed"""
        agent = get_schema_agent()

        schema1 = await agent.infer_schema(prompt=sample_prompt, seed=42)
        schema2 = await agent.infer_schema(prompt=sample_prompt, seed=42)

        # Should produce same structure (though LLM might vary slightly)
        assert schema1["seed"] == schema2["seed"]
        assert len(schema1["tables"]) == len(schema2["tables"])


class TestAgentTools:
    """Test agent tools"""

    @pytest.mark.slow
    @pytest.mark.llm
    def test_analyze_prompt(self, sample_prompt):
        """Test prompt analysis tool"""
        result = analyze_prompt.invoke({"prompt": sample_prompt})

        assert "entities" in result
        assert "domain" in result
        assert isinstance(result["entities"], list)
        assert len(result["entities"]) > 0

    @pytest.mark.slow
    @pytest.mark.llm
    def test_suggest_columns_for_customers(self):
        """Test column suggestion for customers entity"""
        result = suggest_columns.invoke({"entity": "customers", "domain": "ecommerce"})

        assert isinstance(result, list)
        assert len(result) > 0

        # Check for expected columns
        column_names = [col["name"] for col in result]
        assert any("id" in name.lower() for name in column_names)
        assert any("email" in name.lower() for name in column_names)

    @pytest.mark.slow
    @pytest.mark.llm
    def test_infer_relationships(self):
        """Test relationship inference"""
        tables = ["customers", "orders", "transactions"]
        result = infer_relationships.invoke({"tables": tables})

        assert isinstance(result, list)
        # Should find relationship between customers-orders and orders-transactions
        assert len(result) > 0

    @pytest.mark.unit
    def test_validate_valid_schema(self, sample_schema):
        """Test schema validation with valid schema"""
        result = validate_schema.invoke({"schema": sample_schema})

        assert result["valid"] is True
        assert len(result["errors"]) == 0

    @pytest.mark.unit
    def test_validate_invalid_schema(self):
        """Test schema validation with invalid schema"""
        invalid_schema = {"tables": []}  # Empty tables
        result = validate_schema.invoke({"schema": invalid_schema})

        assert result["valid"] is False
        assert len(result["errors"]) > 0

    @pytest.mark.unit
    def test_normalize_schema(self, sample_schema):
        """Test schema normalization"""
        result = normalize_schema.invoke({"schema": sample_schema})

        assert "tables" in result
        assert len(result["tables"]) > 0

        # Check normalized structure
        table = result["tables"][0]
        assert "name" in table
        assert "rows" in table
        assert "columns" in table
        assert isinstance(table["rows"], int)
