"""FastAPI application entry point"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from app.core.config import settings
from app.models.responses import HealthResponse
from app.api import routes_generation, routes_documents, routes_replication, routes_streaming, routes_chat, routes_auth
from app.core.rate_limit import create_limiter, get_rate_limit_exceeded_handler, get_rate_limit_exceeded_error

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""

    # Disable interactive docs in production to reduce attack surface
    _docs_url = None if settings.is_production else f"{settings.API_PREFIX}/docs"
    _redoc_url = None if settings.is_production else f"{settings.API_PREFIX}/redoc"
    _openapi_url = None if settings.is_production else f"{settings.API_PREFIX}/openapi.json"

    app = FastAPI(
        title=settings.API_TITLE,
        version=settings.API_VERSION,
        description="Synthetic Data Studio with Agentic AI",
        docs_url=_docs_url,
        redoc_url=_redoc_url,
        openapi_url=_openapi_url,
    )

    # Rate limiting (no-op if slowapi not installed)
    limiter = create_limiter(default_limit=settings.RATE_LIMIT_DEFAULT)
    if limiter is not None:
        app.state.limiter = limiter
        rate_limit_handler = get_rate_limit_exceeded_handler()
        rate_limit_error = get_rate_limit_exceeded_error()
        if rate_limit_handler and rate_limit_error:
            app.add_exception_handler(rate_limit_error, rate_limit_handler)
        logger.info(f"Rate limiting enabled: {settings.RATE_LIMIT_DEFAULT}")

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )

    # Include routers
    app.include_router(routes_auth.router, prefix=settings.API_PREFIX, tags=["auth"])
    app.include_router(routes_generation.router, prefix=settings.API_PREFIX, tags=["generation"])
    app.include_router(routes_chat.router, prefix=settings.API_PREFIX, tags=["chat"])
    app.include_router(routes_documents.router, prefix=settings.API_PREFIX, tags=["documents"])
    app.include_router(routes_replication.router, prefix=settings.API_PREFIX, tags=["replication"])
    app.include_router(routes_streaming.router, prefix=settings.API_PREFIX, tags=["streaming"])

    # Health check endpoint (both at root and under API prefix)
    @app.get("/healthz", response_model=HealthResponse)
    @app.get(f"{settings.API_PREFIX}/healthz", response_model=HealthResponse)
    async def health_check():
        """Health check endpoint — probes all critical dependencies."""
        service_status: dict[str, str] = {
            "api": "ok",
            "llm_provider": settings.LLM_PROVIDER,
            "storage": "s3" if settings.USE_S3 else "local",
        }
        overall = "healthy"

        # Probe Redis when enabled
        if settings.USE_REDIS:
            try:
                import redis.asyncio as aioredis

                r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
                await r.ping()
                await r.aclose()
                service_status["redis"] = "ok"
            except Exception as exc:
                service_status["redis"] = f"error: {exc}"
                overall = "degraded"

        # Probe AWS Bedrock reachability (lightweight — just describe the model)
        if settings.LLM_PROVIDER == "bedrock":
            try:
                import boto3
                import botocore

                client = boto3.client(
                    "bedrock",
                    region_name=settings.AWS_REGION,
                    **(
                        {
                            "aws_access_key_id": settings.AWS_ACCESS_KEY_ID,
                            "aws_secret_access_key": settings.AWS_SECRET_ACCESS_KEY,
                        }
                        if settings.AWS_ACCESS_KEY_ID
                        else {}
                    ),
                )
                # list_foundation_models is a lightweight read-only call
                client.list_foundation_models(byOutputModality="TEXT")
                service_status["bedrock"] = "ok"
            except Exception as exc:
                service_status["bedrock"] = f"error: {type(exc).__name__}"
                overall = "degraded"

        return HealthResponse(
            status=overall,
            version=settings.API_VERSION,
            services=service_status,
        )

    # Root endpoint
    @app.get("/")
    async def root():
        """Root endpoint"""
        return {
            "service": "DataForge Studio",
            "version": settings.API_VERSION,
            "docs": f"{settings.API_PREFIX}/docs",
        }

    # Exception handlers
    @app.exception_handler(ValueError)
    async def value_error_handler(request, exc):
        return JSONResponse(status_code=400, content={"error": "Bad Request", "detail": str(exc)})

    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal Server Error", "detail": "An unexpected error occurred"},
        )

    logger.info(f"DataForge Studio API started - Version {settings.API_VERSION}")
    logger.info(f"LLM Provider: {settings.LLM_PROVIDER} - Model: {settings.LLM_MODEL}")
    logger.info(f"LangSmith Tracing: {'Enabled' if settings.LANGCHAIN_TRACING_V2 else 'Disabled'}")

    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
