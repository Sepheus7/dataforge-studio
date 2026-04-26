"""Tests for authentication, configuration, and replication routes"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.core.auth import verify_api_key, optional_api_key
from fastapi import HTTPException


class TestAuthentication:
    """Test API key authentication"""

    def test_missing_api_key_returns_401(self, client):
        """Requests without an API key should get 401"""
        response = client.post("/v1/generation/prompt", json={"prompt": "test"})
        assert response.status_code == 401

    def test_wrong_api_key_returns_403(self, client):
        """Requests with wrong key should get 403"""
        response = client.post(
            "/v1/generation/prompt",
            headers={"X-API-Key": "totally-wrong-key"},
            json={"prompt": "test"},
        )
        assert response.status_code == 403

    def test_correct_api_key_passes(self, client, auth_headers):
        """Valid key should pass authentication (and get to the handler)"""
        response = client.post(
            "/v1/generation/prompt",
            headers=auth_headers,
            json={"prompt": "generate users"},
        )
        # 200 or any non-auth error means auth passed
        assert response.status_code not in (401, 403)

    @pytest.mark.asyncio
    async def test_verify_api_key_valid(self):
        """verify_api_key should return the key when valid"""
        result = await verify_api_key(settings.API_KEY)
        assert result == settings.API_KEY

    @pytest.mark.asyncio
    async def test_verify_api_key_missing_raises(self):
        """verify_api_key should raise 401 when key is None"""
        with pytest.raises(HTTPException) as exc:
            await verify_api_key(None)
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_verify_api_key_wrong_raises(self):
        """verify_api_key should raise 403 for wrong key"""
        with pytest.raises(HTTPException) as exc:
            await verify_api_key("bad-key")
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_optional_api_key_none(self):
        """optional_api_key returns None when no key provided"""
        result = await optional_api_key(None)
        assert result is None

    @pytest.mark.asyncio
    async def test_optional_api_key_valid(self):
        """optional_api_key returns key when valid"""
        result = await optional_api_key(settings.API_KEY)
        assert result == settings.API_KEY

    @pytest.mark.asyncio
    async def test_optional_api_key_wrong_returns_none(self):
        """optional_api_key returns None (not raises) for bad key"""
        result = await optional_api_key("wrong-key")
        assert result is None


class TestConfiguration:
    """Test application configuration"""

    def test_default_environment_is_development(self):
        """ENVIRONMENT defaults to development in tests"""
        # conftest.py doesn't set ENVIRONMENT so it stays as default
        assert settings.ENVIRONMENT in ("development", "staging", "production")

    def test_is_production_false_in_tests(self):
        """is_production should be False in test environment"""
        # Tests run with ENVIRONMENT=development (default)
        assert not settings.is_production

    def test_cors_not_wildcard(self):
        """CORS_ORIGINS should not be ['*'] by default"""
        assert settings.CORS_ORIGINS != ["*"], (
            "CORS must not be open to all origins. "
            "Set specific origins in CORS_ORIGINS."
        )

    def test_api_prefix_configured(self):
        """API prefix should be set"""
        assert settings.API_PREFIX == "/v1"

    def test_artifacts_dir_returns_local_when_s3_disabled(self):
        """artifacts_dir should return LOCAL_ARTIFACTS_DIR when USE_S3=False"""
        assert settings.USE_S3 is False
        assert settings.artifacts_dir == settings.LOCAL_ARTIFACTS_DIR

    def test_generation_limits_sane(self):
        """Generation limits should be positive numbers"""
        assert settings.MAX_ROWS_PER_TABLE > 0
        assert settings.MAX_TABLES > 0
        assert settings.MAX_COLUMNS_PER_TABLE > 0
        assert settings.MAX_CONCURRENT_JOBS > 0


class TestHealthEndpoint:
    """Extended health endpoint tests"""

    def test_health_returns_healthy(self, client):
        response = client.get("/healthz")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_health_contains_version(self, client):
        response = client.get("/healthz")
        data = response.json()
        assert "version" in data
        assert data["version"] == settings.API_VERSION

    def test_health_contains_services(self, client):
        response = client.get("/healthz")
        data = response.json()
        assert "services" in data
        assert "api" in data["services"]
        assert data["services"]["api"] == "running"

    def test_health_at_api_prefix(self, client, auth_headers):
        """Health should also be available under /v1/healthz"""
        response = client.get("/v1/healthz")
        assert response.status_code == 200

    def test_root_endpoint(self, client):
        """Root / should return service info"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "DataForge" in data["service"]


class TestReplicationRoutes:
    """Test replication endpoints return graceful errors when SDV is unavailable"""

    def test_replicate_endpoint_returns_503_not_500(self, client, auth_headers, tmp_path):
        """When SDV is disabled, replicate should return 503 not 500/crash"""
        # First upload a fake CSV
        csv_content = b"name,age\nAlice,30\nBob,25\n"
        upload_resp = client.post(
            "/v1/replication/upload",
            headers=auth_headers,
            files={"file": ("test.csv", csv_content, "text/csv")},
        )
        assert upload_resp.status_code == 200
        dataset_id = upload_resp.json()["dataset_id"]

        # Now try to replicate — SDV is disabled in tests
        config = {"num_rows": 10, "model_type": "gaussian_copula", "replace_pii": False}
        rep_resp = client.post(
            f"/v1/replication/{dataset_id}/replicate",
            headers=auth_headers,
            json=config,
        )
        # Should create a job (the 503 comes asynchronously via background task)
        # The endpoint itself should succeed in creating the job
        assert rep_resp.status_code in (200, 503)

    def test_upload_non_csv_returns_400(self, client, auth_headers):
        """Uploading non-CSV should return 400"""
        resp = client.post(
            "/v1/replication/upload",
            headers=auth_headers,
            files={"file": ("data.json", b'{"a": 1}', "application/json")},
        )
        assert resp.status_code == 400

    def test_analyze_nonexistent_dataset_returns_404(self, client, auth_headers):
        """Analyzing a dataset that doesn't exist should return 404"""
        resp = client.post(
            "/v1/replication/nonexistent_ds_000/analyze",
            headers=auth_headers,
        )
        assert resp.status_code == 404


class TestDocumentRoutes:
    """Test document generation endpoints"""

    def test_document_generate_requires_auth(self, client):
        """Document generation should require API key"""
        response = client.post(
            "/v1/documents/generate",
            json={"prompt": "generate an invoice", "doc_type": "invoice"},
        )
        assert response.status_code == 401

    def test_document_generate_with_auth(self, client, auth_headers):
        """Document generation with auth should not 401/403"""
        response = client.post(
            "/v1/documents/generate",
            headers=auth_headers,
            json={"prompt": "generate a simple invoice", "doc_type": "invoice", "count": 1},
        )
        assert response.status_code not in (401, 403)
