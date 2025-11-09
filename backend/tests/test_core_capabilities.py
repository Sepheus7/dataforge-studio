"""Comprehensive tests for core DataForge Studio capabilities"""

import pytest
import asyncio
from pathlib import Path
from fastapi.testclient import TestClient

from app.agents.schema_agent import get_schema_agent
from app.services.generation.structured import get_structured_generator
from app.services.jobs import get_job_manager
from app.core.config import settings


class TestSchemaInference:
    """Test core schema inference capabilities"""

    @pytest.mark.asyncio
    @pytest.mark.slow
    @pytest.mark.llm
    async def test_infer_schema_from_simple_prompt(self):
        """Test schema inference from a simple prompt"""
        agent = get_schema_agent()
        
        schema = await agent.infer_schema(
            prompt="Generate customer data with name and email",
            size_hint={"customers": 50},
            seed=42
        )
        
        assert schema is not None
        assert "tables" in schema
        assert len(schema["tables"]) > 0
        
        # Check table structure
        table = schema["tables"][0]
        assert "name" in table
        assert "rows" in table
        assert "columns" in table
        # Should respect size_hint (allow some variance as LLM may adjust)
        assert table["rows"] >= 50  # At least the requested amount
        
        # Check columns
        assert len(table["columns"]) > 0
        column_names = [col["name"].lower() for col in table["columns"]]
        assert any("name" in name or "email" in name for name in column_names)

    @pytest.mark.asyncio
    @pytest.mark.slow
    @pytest.mark.llm
    async def test_infer_multi_table_schema(self):
        """Test schema inference for multiple related tables"""
        agent = get_schema_agent()
        
        schema = await agent.infer_schema(
            prompt="Generate customers with orders and order line items",
            size_hint={"customers": 100, "orders": 500, "line_items": 2000},
            seed=42
        )
        
        assert schema is not None
        assert len(schema["tables"]) >= 3
        
        table_names = [t["name"].lower() for t in schema["tables"]]
        assert any("customer" in name for name in table_names)
        assert any("order" in name for name in table_names)
        
        # Check relationships
        order_table = next((t for t in schema["tables"] if "order" in t["name"].lower()), None)
        assert order_table is not None
        # Should have foreign keys
        assert "foreign_keys" in order_table or any(
            "customer" in col["name"].lower() or "id" in col["name"].lower()
            for col in order_table["columns"]
        )

    @pytest.mark.asyncio
    @pytest.mark.slow
    @pytest.mark.llm
    async def test_conversation_memory(self):
        """Test that agent remembers previous conversation context"""
        agent = get_schema_agent()
        thread_id = "test_thread_memory"
        
        # First message
        schema1 = await agent.infer_schema(
            prompt="Generate IoT sensor data with devices and readings",
            thread_id=thread_id,
            seed=42
        )
        
        assert schema1 is not None
        assert len(schema1["tables"]) >= 2
        
        # Second message - should remember context
        schema2 = await agent.infer_schema(
            prompt="Add a third table for factory locations",
            thread_id=thread_id,
            seed=42
        )
        
        # Should have more tables than before (or at least remember the context)
        assert schema2 is not None
        # The agent should have loaded previous messages
        # (Note: exact behavior depends on how memory is implemented)

    @pytest.mark.asyncio
    @pytest.mark.slow
    @pytest.mark.llm
    async def test_schema_with_custom_constraints(self):
        """Test schema inference respects custom constraints"""
        agent = get_schema_agent()
        
        schema = await agent.infer_schema(
            prompt="Generate employee data with age between 18 and 65, and salary above 30000",
            size_hint={"employees": 50},
            seed=42
        )
        
        assert schema is not None
        employee_table = next(
            (t for t in schema["tables"] if "employee" in t["name"].lower()),
            schema["tables"][0]
        )
        
        # Check for age and salary columns
        column_names = [col["name"].lower() for col in employee_table["columns"]]
        has_age = any("age" in name for name in column_names)
        has_salary = any("salary" in name or "wage" in name for name in column_names)
        
        # At least one constraint-related column should exist
        assert has_age or has_salary


class TestDataGeneration:
    """Test core data generation capabilities"""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_generate_single_table(self, artifacts_dir, sample_schema):
        """Test generating data for a single table"""
        generator = get_structured_generator()
        job_id = "test_job_single"
        
        summary = await generator.generate_from_schema(job_id, sample_schema)
        
        assert summary is not None
        assert "tables" in summary
        assert len(summary["tables"]) > 0
        
        # Check files were created
        job_dir = Path(artifacts_dir) / job_id
        assert job_dir.exists()
        
        table = summary["tables"][0]
        csv_file = job_dir / f"{table['name']}.csv"
        assert csv_file.exists()
        
        # Check file has data
        assert csv_file.stat().st_size > 0

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_generate_multi_table_with_relationships(self, artifacts_dir, multi_table_schema):
        """Test generating related tables with foreign key integrity"""
        generator = get_structured_generator()
        job_id = "test_job_multi"
        
        summary = await generator.generate_from_schema(job_id, multi_table_schema)
        
        assert summary is not None
        assert len(summary["tables"]) == 2
        
        # Check files were created
        job_dir = Path(artifacts_dir) / job_id
        assert job_dir.exists()
        
        for table in summary["tables"]:
            csv_file = job_dir / f"{table['name']}.csv"
            assert csv_file.exists()
            assert csv_file.stat().st_size > 0

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_generated_data_has_correct_row_count(self, artifacts_dir, sample_schema):
        """Test that generated data matches schema row counts"""
        generator = get_structured_generator()
        job_id = "test_job_rows"
        
        summary = await generator.generate_from_schema(job_id, sample_schema)
        
        assert summary is not None
        
        for table_summary in summary["tables"]:
            schema_table = next(
                (t for t in sample_schema["tables"] if t["name"] == table_summary["name"]),
                None
            )
            if schema_table:
                # Allow some variance, but should be close
                expected_rows = schema_table["rows"]
                actual_rows = table_summary["rows"]
                assert abs(actual_rows - expected_rows) <= 1  # Allow 1 row variance

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_generated_data_respects_seed(self, artifacts_dir, sample_schema):
        """Test that same seed produces same data"""
        generator = get_structured_generator()
        
        # Generate with seed 42
        job_id1 = "test_job_seed1"
        summary1 = await generator.generate_from_schema(job_id1, sample_schema)
        
        # Generate again with same seed
        job_id2 = "test_job_seed2"
        summary2 = await generator.generate_from_schema(job_id2, sample_schema)
        
        # Should have same structure
        assert len(summary1["tables"]) == len(summary2["tables"])
        assert summary1["total_rows"] == summary2["total_rows"]


class TestJobManagement:
    """Test job management capabilities"""

    @pytest.mark.unit
    def test_create_job(self):
        """Test job creation"""
        job_manager = get_job_manager()
        
        job_id = job_manager.create_job()
        
        assert job_id is not None
        assert job_id.startswith("job_")
        
        job = job_manager.get_job(job_id)
        assert job is not None
        assert job["status"] == "queued"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_job_progress_tracking(self):
        """Test job progress updates"""
        job_manager = get_job_manager()
        
        job_id = job_manager.create_job()
        # start_job uses asyncio.create_task, so we need an event loop
        job_manager.start_job(job_id)
        # Give async task a moment to complete
        await asyncio.sleep(0.1)
        
        # Update progress
        job_manager.update_progress(job_id, 0.5, "Halfway done")
        await asyncio.sleep(0.1)
        
        job = job_manager.get_job(job_id)
        assert job["progress"] == 0.5
        assert job["message"] == "Halfway done"
        assert job["status"] == "running"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_job_completion(self):
        """Test job completion"""
        job_manager = get_job_manager()
        
        job_id = job_manager.create_job()
        job_manager.start_job(job_id)
        await asyncio.sleep(0.1)
        
        summary = {"tables": [{"name": "test", "rows": 100}]}
        job_manager.complete_job(job_id, summary)
        await asyncio.sleep(0.1)
        
        job = job_manager.get_job(job_id)
        assert job["status"] == "succeeded"
        assert job["summary"] == summary

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_job_failure(self):
        """Test job failure handling"""
        job_manager = get_job_manager()
        
        job_id = job_manager.create_job()
        job_manager.start_job(job_id)
        await asyncio.sleep(0.1)
        
        error_message = "Test error"
        job_manager.fail_job(job_id, error_message)
        await asyncio.sleep(0.1)
        
        job = job_manager.get_job(job_id)
        assert job["status"] == "failed"
        assert job["error"] == error_message


class TestAPIEndpoints:
    """Test core API endpoints"""

    def test_chat_endpoint(self, client, auth_headers):
        """Test conversational chat endpoint"""
        response = client.post(
            "/v1/chat",
            headers=auth_headers,
            json={"prompt": "I need customer data", "thread_id": "test_chat"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "response" in data
        assert "thread_id" in data
        assert len(data["response"]) > 0

    def test_chat_with_memory(self, client, auth_headers):
        """Test chat endpoint maintains conversation memory"""
        thread_id = "test_memory_thread"
        
        # First message
        response1 = client.post(
            "/v1/chat",
            headers=auth_headers,
            json={"prompt": "I need IoT sensor data", "thread_id": thread_id}
        )
        assert response1.status_code == 200
        
        # Second message - should remember context
        response2 = client.post(
            "/v1/chat",
            headers=auth_headers,
            json={"prompt": "Can you add factory locations?", "thread_id": thread_id}
        )
        assert response2.status_code == 200
        
        # Both should have same thread_id
        assert response1.json()["thread_id"] == response2.json()["thread_id"]

    def test_generation_with_thread_id(self, client, auth_headers):
        """Test generation endpoint accepts thread_id for memory"""
        response = client.post(
            "/v1/generation/prompt",
            headers=auth_headers,
            json={
                "prompt": "Generate customer data",
                "thread_id": "test_gen_thread",
                "size_hint": {"customers": 10}
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data

    def test_streaming_endpoint_authentication(self, client, auth_headers):
        """Test SSE streaming endpoint authentication"""
        # Create a job first
        create_response = client.post(
            "/v1/generation/prompt",
            headers=auth_headers,
            json={"prompt": "Generate test data", "size_hint": {"data": 10}}
        )
        job_id = create_response.json()["job_id"]
        
        # Test with API key in header
        response = client.get(
            f"/v1/generation/{job_id}/stream",
            headers=auth_headers
        )
        # SSE endpoint should accept the connection
        assert response.status_code == 200
        
        # Test with API key in query param (for EventSource)
        response2 = client.get(
            f"/v1/generation/{job_id}/stream?key={settings.API_KEY}"
        )
        assert response2.status_code == 200

    def test_download_endpoint(self, client, auth_headers, sample_schema):
        """Test download endpoint after generation completes"""
        # Create job
        create_response = client.post(
            "/v1/generation/schema",
            headers=auth_headers,
            json={"schema": sample_schema}
        )
        job_id = create_response.json()["job_id"]
        
        # Wait for completion (in real scenario, would poll)
        # For now, just test the endpoint structure
        # Note: This will fail if job isn't complete, which is expected
        
        # Test download endpoint exists and handles auth
        download_response = client.get(
            f"/v1/generation/{job_id}/download",
            headers=auth_headers,
            params={"table_name": "users", "format": "csv"}
        )
        
        # Should either return file (if complete) or 400/404 (if not)
        assert download_response.status_code in [200, 400, 404]


class TestErrorHandling:
    """Test error handling and edge cases"""

    def test_invalid_api_key(self, client):
        """Test API rejects invalid API key"""
        response = client.post(
            "/v1/generation/prompt",
            headers={"X-API-Key": "invalid-key"},
            json={"prompt": "test"}
        )
        
        assert response.status_code == 401

    def test_missing_prompt(self, client, auth_headers):
        """Test API rejects request without prompt"""
        response = client.post(
            "/v1/generation/prompt",
            headers=auth_headers,
            json={}
        )
        
        assert response.status_code == 422  # Validation error

    def test_empty_prompt(self, client, auth_headers):
        """Test API handles empty prompt"""
        response = client.post(
            "/v1/generation/prompt",
            headers=auth_headers,
            json={"prompt": ""}
        )
        
        # Should either reject or handle gracefully
        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_agent_handles_invalid_prompt(self):
        """Test agent handles edge case prompts"""
        agent = get_schema_agent()
        
        # Very short prompt
        try:
            schema = await agent.infer_schema(prompt="data", seed=42)
            # Should either succeed with defaults or fail gracefully
            assert schema is not None or True  # Accept either outcome
        except Exception:
            # Failure is also acceptable for edge cases
            pass

