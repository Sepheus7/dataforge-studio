"""Tests for FastAPI endpoints"""

import pytest
import time
from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """Test health check endpoint"""

    def test_health_check(self, client):
        """Test health endpoint"""
        response = client.get("/healthz")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


class TestGenerationAPI:
    """Test data generation API"""

    def test_generate_from_prompt_without_auth(self, client, sample_prompt):
        """Test that API requires authentication"""
        response = client.post("/v1/generation/prompt", json={"prompt": sample_prompt})
        assert response.status_code == 401

    def test_generate_from_prompt(self, client, auth_headers, sample_prompt):
        """Test generation from prompt"""
        response = client.post(
            "/v1/generation/prompt",
            headers=auth_headers,
            json={"prompt": sample_prompt, "size_hint": {"customers": 50}, "seed": 42},
        )

        assert response.status_code == 200
        data = response.json()

        assert "job_id" in data
        assert data["status"] == "queued"
        assert data["job_id"].startswith("job_")

    def test_generate_from_schema(self, client, auth_headers, sample_schema):
        """Test generation from schema"""
        response = client.post(
            "/v1/generation/schema", headers=auth_headers, json={"schema": sample_schema}
        )

        assert response.status_code == 200
        data = response.json()

        assert "job_id" in data
        assert data["status"] == "queued"

    def test_get_job_status(self, client, auth_headers, sample_schema):
        """Test getting job status"""
        # Create job
        create_response = client.post(
            "/v1/generation/schema", headers=auth_headers, json={"schema": sample_schema}
        )
        job_id = create_response.json()["job_id"]

        # Get status
        status_response = client.get(f"/v1/generation/{job_id}", headers=auth_headers)

        assert status_response.status_code == 200
        data = status_response.json()

        assert data["job_id"] == job_id
        assert "status" in data
        assert "progress" in data

    def test_get_nonexistent_job(self, client, auth_headers):
        """Test getting status of nonexistent job"""
        response = client.get("/v1/generation/nonexistent_job", headers=auth_headers)

        assert response.status_code == 404

    def test_download_artifacts_incomplete_job(self, client, auth_headers, sample_schema):
        """Test downloading from incomplete job"""
        # Create job
        create_response = client.post(
            "/v1/generation/schema", headers=auth_headers, json={"schema": sample_schema}
        )
        job_id = create_response.json()["job_id"]

        # Try to download immediately (should fail)
        download_response = client.get(
            f"/v1/generation/{job_id}/download",
            headers=auth_headers,
            params={"table_name": "users", "format": "csv"},
        )

        assert download_response.status_code == 400


class TestDocumentAPI:
    """Test document generation API"""

    def test_generate_document(self, client, auth_headers):
        """Test document generation"""
        response = client.post(
            "/v1/documents/generate",
            headers=auth_headers,
            json={"document_type": "invoice", "format": "pdf", "count": 1},
        )

        assert response.status_code == 200
        data = response.json()

        assert "job_id" in data
        assert data["status"] == "queued"


class TestReplicationAPI:
    """Test dataset replication API"""

    def test_upload_dataset(self, client, auth_headers):
        """Test dataset upload"""
        # Create CSV content
        csv_content = "id,name,value\n1,Alice,100\n2,Bob,200\n"

        response = client.post(
            "/v1/replication/upload",
            headers=auth_headers,
            files={"file": ("test.csv", csv_content, "text/csv")},
        )

        assert response.status_code == 200
        data = response.json()

        assert "dataset_id" in data
        assert data["dataset_id"].startswith("ds_")

    def test_upload_invalid_file(self, client, auth_headers):
        """Test uploading non-CSV file"""
        response = client.post(
            "/v1/replication/upload",
            headers=auth_headers,
            files={"file": ("test.txt", "not a csv", "text/plain")},
        )

        assert response.status_code == 400

    def test_analyze_dataset(self, client, auth_headers):
        """Test dataset analysis"""
        # Upload dataset first
        csv_content = "id,name,email\n1,Alice,alice@example.com\n2,Bob,bob@example.com\n"
        upload_response = client.post(
            "/v1/replication/upload",
            headers=auth_headers,
            files={"file": ("test.csv", csv_content, "text/csv")},
        )
        dataset_id = upload_response.json()["dataset_id"]

        # Analyze
        analyze_response = client.post(
            f"/v1/replication/{dataset_id}/analyze", headers=auth_headers
        )

        assert analyze_response.status_code == 200
        data = analyze_response.json()

        assert data["dataset_id"] == dataset_id
        assert data["total_rows"] == 2
        assert data["total_columns"] == 3

    def test_replicate_dataset(self, client, auth_headers):
        """Test dataset replication"""
        # Upload dataset first
        csv_content = "id,value\n" + "\n".join([f"{i},{i*10}" for i in range(1, 101)])
        upload_response = client.post(
            "/v1/replication/upload",
            headers=auth_headers,
            files={"file": ("test.csv", csv_content, "text/csv")},
        )
        dataset_id = upload_response.json()["dataset_id"]

        # Replicate
        replicate_response = client.post(
            f"/v1/replication/{dataset_id}/replicate",
            headers=auth_headers,
            json={
                "num_rows": 50,
                "model_type": "gaussian_copula",
                "replace_pii": False,
                "preserve_relationships": True,
                "quality_threshold": 0.7,
            },
        )

        assert replicate_response.status_code == 200
        data = replicate_response.json()

        assert "job_id" in data
        assert data["status"] == "queued"


class TestStreamingAPI:
    """Test SSE streaming"""

    def test_stream_job_progress(self, client, auth_headers, sample_schema):
        """Test SSE streaming endpoint"""
        # Create job
        create_response = client.post(
            "/v1/generation/schema", headers=auth_headers, json={"schema": sample_schema}
        )
        job_id = create_response.json()["job_id"]

        # Test streaming endpoint exists (actual streaming tested manually)
        response = client.get(f"/v1/generation/{job_id}/stream", headers=auth_headers)

        # Should connect successfully
        assert response.status_code == 200
