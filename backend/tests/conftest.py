"""Pytest configuration and fixtures"""

import pytest
import os
from pathlib import Path
import tempfile
import shutil
from fastapi.testclient import TestClient

# Set test environment variables
os.environ["API_KEY"] = "test-api-key"
os.environ["LANGCHAIN_TRACING_V2"] = "false"  # Disable for tests
os.environ["USE_S3"] = "false"
os.environ["USE_REDIS"] = "false"

from app.main import app
from app.core.config import settings


@pytest.fixture(scope="session")
def test_artifacts_dir():
    """Create temporary directory for test artifacts"""
    temp_dir = Path(tempfile.mkdtemp(prefix="dataforge_test_"))
    yield temp_dir
    # Cleanup after all tests
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="function")
def artifacts_dir(test_artifacts_dir):
    """Create clean artifacts directory for each test"""
    test_dir = test_artifacts_dir / f"test_{os.getpid()}"
    test_dir.mkdir(parents=True, exist_ok=True)

    # Override settings
    settings.LOCAL_ARTIFACTS_DIR = str(test_dir)

    yield test_dir

    # Cleanup after test
    if test_dir.exists():
        shutil.rmtree(test_dir, ignore_errors=True)


@pytest.fixture(scope="module")
def client():
    """FastAPI test client"""
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Authentication headers for API requests"""
    return {"X-API-Key": settings.API_KEY}


@pytest.fixture
def sample_schema():
    """Sample data schema for testing"""
    return {
        "seed": 42,
        "tables": [
            {
                "name": "users",
                "rows": 100,
                "primary_key": "user_id",
                "columns": [
                    {"name": "user_id", "type": "uuid", "unique": True},
                    {"name": "username", "type": "string"},
                    {"name": "email", "type": "email", "unique": True},
                    {"name": "age", "type": "int", "range": {"min": 18, "max": 80}},
                    {"name": "created_at", "type": "datetime"},
                ],
            }
        ],
    }


@pytest.fixture
def multi_table_schema():
    """Multi-table schema with relationships"""
    return {
        "seed": 42,
        "tables": [
            {
                "name": "customers",
                "rows": 50,
                "primary_key": "customer_id",
                "columns": [
                    {"name": "customer_id", "type": "uuid", "unique": True},
                    {"name": "name", "type": "string"},
                    {"name": "email", "type": "email"},
                ],
            },
            {
                "name": "orders",
                "rows": 200,
                "primary_key": "order_id",
                "foreign_keys": [
                    {"column": "customer_id", "ref_table": "customers", "ref_column": "customer_id"}
                ],
                "columns": [
                    {"name": "order_id", "type": "uuid", "unique": True},
                    {"name": "customer_id", "type": "uuid"},
                    {"name": "amount", "type": "float"},
                    {
                        "name": "status",
                        "type": "categorical",
                        "categories": ["pending", "shipped", "delivered"],
                    },
                ],
            },
        ],
    }


@pytest.fixture
def sample_prompt():
    """Sample prompt for agent testing"""
    return "Generate a dataset with customers and orders for an ecommerce business"
