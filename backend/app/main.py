"""FastAPI application entry point"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from app.core.config import settings
from app.models.responses import HealthResponse
from app.api import routes_generation, routes_documents, routes_replication, routes_streaming, routes_chat

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""

    app = FastAPI(
        title=settings.API_TITLE,
        version=settings.API_VERSION,
        description="Synthetic Data Studio with Agentic AI",
        docs_url=f"{settings.API_PREFIX}/docs",
        redoc_url=f"{settings.API_PREFIX}/redoc",
        openapi_url=f"{settings.API_PREFIX}/openapi.json",
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )

    # Include routers
    app.include_router(routes_generation.router, prefix=settings.API_PREFIX, tags=["generation"])
    app.include_router(routes_chat.router, prefix=settings.API_PREFIX, tags=["chat"])
    app.include_router(routes_documents.router, prefix=settings.API_PREFIX, tags=["documents"])
    app.include_router(routes_replication.router, prefix=settings.API_PREFIX, tags=["replication"])
    app.include_router(routes_streaming.router, prefix=settings.API_PREFIX, tags=["streaming"])

    # Health check endpoint (both at root and under API prefix)
    @app.get("/healthz", response_model=HealthResponse)
    @app.get(f"{settings.API_PREFIX}/healthz", response_model=HealthResponse)
    async def health_check():
        """Health check endpoint"""
        return HealthResponse(
            status="healthy",
            version=settings.API_VERSION,
            services={
                "api": "running",
                "llm_provider": settings.LLM_PROVIDER,
                "storage": "s3" if settings.USE_S3 else "local",
            },
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
