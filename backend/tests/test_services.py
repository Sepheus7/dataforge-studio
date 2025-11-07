"""Tests for service layer"""

import pytest
import pandas as pd
from pathlib import Path

from app.services.generation.structured import get_structured_generator
from app.services.pii.detector import get_pii_detector
from app.services.pii.replacer import get_pii_replacer
from app.services.generation.sdv_wrapper import get_sdv_replicator
from app.services.jobs import get_job_manager


class TestStructuredGeneration:
    """Test structured data generation"""

    @pytest.mark.asyncio
    async def test_generate_from_schema(self, sample_schema, artifacts_dir):
        """Test data generation from schema"""
        generator = get_structured_generator(base_dir=artifacts_dir)
        job_id = "test_job_001"

        summary = await generator.generate_from_schema(job_id, sample_schema)

        assert summary is not None
        assert "tables" in summary
        assert len(summary["tables"]) == 1
        assert summary["tables"][0]["rows"] == 100

        # Check artifacts exist
        job_dir = artifacts_dir / job_id
        assert job_dir.exists()
        assert (job_dir / "users.csv").exists()
        assert (job_dir / "users.json").exists()

    @pytest.mark.asyncio
    async def test_multi_table_generation(self, multi_table_schema, artifacts_dir):
        """Test multi-table generation with foreign keys"""
        generator = get_structured_generator(base_dir=artifacts_dir)
        job_id = "test_job_002"

        summary = await generator.generate_from_schema(job_id, multi_table_schema)

        assert len(summary["tables"]) == 2

        # Check both tables generated
        job_dir = artifacts_dir / job_id
        assert (job_dir / "customers.csv").exists()
        assert (job_dir / "orders.csv").exists()

        # Verify foreign key integrity
        customers_df = pd.read_csv(job_dir / "customers.csv")
        orders_df = pd.read_csv(job_dir / "orders.csv")

        customer_ids = set(customers_df["customer_id"])
        order_customer_ids = set(orders_df["customer_id"])

        # All order customer_ids should exist in customers
        assert order_customer_ids.issubset(customer_ids)


class TestPII:
    """Test PII detection and replacement"""

    def test_detect_pii_in_dataframe(self):
        """Test PII detection in DataFrame"""
        df = pd.DataFrame(
            {
                "name": ["John Doe", "Jane Smith"],
                "email": ["john@example.com", "jane@example.com"],
                "phone": ["555-123-4567", "555-987-6543"],
                "age": [30, 25],
            }
        )

        detector = get_pii_detector()
        pii_map = detector.detect_in_dataframe(df)

        assert "email" in pii_map
        assert "phone" in pii_map
        assert "name" in pii_map
        assert "age" not in pii_map  # Not PII

    def test_replace_pii(self):
        """Test PII replacement"""
        df = pd.DataFrame(
            {"name": ["John Doe", "Jane Smith"], "email": ["john@example.com", "jane@example.com"]}
        )

        pii_map = {"name": ["person_name"], "email": ["email"]}

        replacer = get_pii_replacer(seed=42)
        replaced_df = replacer.replace_in_dataframe(df, pii_map, strategy="fake")

        # Should be different from original
        assert not replaced_df["name"].equals(df["name"])
        assert not replaced_df["email"].equals(df["email"])

        # Should still have valid format
        assert "@" in replaced_df["email"].iloc[0]


class TestSDV:
    """Test SDV wrapper"""

    def test_analyze_dataset(self):
        """Test dataset analysis"""
        df = pd.DataFrame(
            {
                "id": [1, 2, 3, 4, 5],
                "name": ["Alice", "Bob", "Charlie", "David", "Eve"],
                "age": [25, 30, 35, 40, 45],
                "city": ["NYC", "LA", "NYC", "SF", "LA"],
            }
        )

        sdv = get_sdv_replicator()
        analysis = sdv.analyze_dataset(df, "test_table")

        assert analysis["num_rows"] == 5
        assert analysis["num_columns"] == 4
        assert len(analysis["columns"]) == 4

    def test_train_and_generate(self):
        """Test model training and synthesis"""
        df = pd.DataFrame(
            {
                "id": list(range(100)),
                "value": [i * 2 for i in range(100)],
                "category": ["A", "B", "C"] * 33 + ["A"],
            }
        )

        sdv = get_sdv_replicator()

        # Train model
        model_id = sdv.train_model(df, model_type="gaussian_copula", table_name="test")
        assert model_id is not None

        # Generate synthetic data
        synthetic_df = sdv.generate_synthetic(model_id, num_rows=50)
        assert len(synthetic_df) == 50
        assert list(synthetic_df.columns) == list(df.columns)


class TestJobManager:
    """Test job management"""

    def test_create_job(self):
        """Test job creation"""
        manager = get_job_manager()
        job_id = manager.create_job()

        assert job_id is not None
        assert job_id.startswith("job_")

        job = manager.get_job(job_id)
        assert job is not None
        assert job["status"] == "queued"

    def test_job_lifecycle(self):
        """Test complete job lifecycle"""
        manager = get_job_manager()
        job_id = manager.create_job()

        # Start job
        manager.start_job(job_id)
        job = manager.get_job(job_id)
        assert job["status"] == "running"

        # Update progress
        manager.update_progress(job_id, 0.5, "Half done")
        job = manager.get_job(job_id)
        assert job["progress"] == 0.5

        # Complete job
        manager.complete_job(job_id, {"result": "success"})
        job = manager.get_job(job_id)
        assert job["status"] == "succeeded"
        assert job["summary"]["result"] == "success"

    def test_fail_job(self):
        """Test job failure"""
        manager = get_job_manager()
        job_id = manager.create_job()

        manager.fail_job(job_id, "Test error")
        job = manager.get_job(job_id)

        assert job["status"] == "failed"
        assert job["error"] == "Test error"
