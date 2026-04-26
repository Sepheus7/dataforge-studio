"""Application configuration using pydantic-settings"""

from typing import Optional
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Get the project root directory (4 levels up from config.py)
# __file__ = .../backend/app/core/config.py
# .parent → app/core
# .parent → app  
# .parent → backend
# .parent → PROJECT ROOT
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow"
    )

    # Environment: "development" | "staging" | "production"
    ENVIRONMENT: str = "development"

    # JWT Authentication (set ENABLE_JWT_AUTH=true to require Bearer tokens)
    ENABLE_JWT_AUTH: bool = False
    JWT_SECRET_KEY: Optional[str] = None  # Must be set when ENABLE_JWT_AUTH=true
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = False  # Set to true in production
    RATE_LIMIT_DEFAULT: str = "60/minute"
    RATE_LIMIT_GENERATION: str = "10/minute"

    # API Configuration
    API_KEY: str = "dev-key"
    API_PREFIX: str = "/v1"
    API_TITLE: str = "DataForge Studio API"
    API_VERSION: str = "0.1.0"

    # AWS Bedrock AgentCore
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    BEDROCK_AGENT_ID: Optional[str] = None
    BEDROCK_AGENT_ALIAS_ID: Optional[str] = None

    # LLM Configuration - Claude models
    LLM_PROVIDER: str = "bedrock"  # bedrock, openai, anthropic
    # Options:
    # - "us.anthropic.claude-3-5-sonnet-20241022-v2:0" (cross-region inference profile)
    # - "anthropic.claude-3-5-sonnet-20241022-v2:0" (direct model access)
    # - "anthropic.claude-3-haiku-20240307-v1:0" (Claude 3 Haiku - cheaper)
    LLM_MODEL: str = "arn:aws:bedrock:us-east-1:842676020002:inference-profile/us.anthropic.claude-haiku-4-5-20251001-v1:0"
    LLM_TEMPERATURE: float = 0.2
    LLM_MAX_TOKENS: int = 4096
    LLM_STREAMING: bool = True

    # LangSmith Configuration (for agent evaluation & testing)
    LANGCHAIN_TRACING_V2: bool = True
    LANGCHAIN_API_KEY: Optional[str] = None
    LANGCHAIN_PROJECT: str = "dataforge-studio"
    LANGCHAIN_ENDPOINT: str = "https://api.smith.langchain.com"

    # Storage Configuration
    S3_BUCKET: Optional[str] = None
    S3_REGION: str = "us-east-1"
    S3_PREFIX: str = "artifacts"
    LOCAL_ARTIFACTS_DIR: str = "artifacts"
    USE_S3: bool = False  # Set to True in production

    # Redis/Memory Configuration
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    REDIS_TTL: int = 3600  # 1 hour
    USE_REDIS: bool = False  # Set to True in production

    # Generation Limits
    MAX_ROWS_PER_TABLE: int = 1_000_000
    MAX_TABLES: int = 50
    MAX_COLUMNS_PER_TABLE: int = 200
    MAX_CONCURRENT_JOBS: int = 10
    JOB_TIMEOUT_SECONDS: int = 3600  # 1 hour

    # Spacy Configuration for PII detection
    SPACY_MODEL: str = "en_core_web_sm"
    PII_DETECTION_ENABLED: bool = True

    # CORS Configuration
    # In production set CORS_ORIGINS to your actual frontend URL(s), e.g.:
    #   CORS_ORIGINS=["https://app.yourdomain.com"]
    # Wildcard ("*") is only acceptable for local development.
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    CORS_ALLOW_HEADERS: list[str] = ["*"]

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json or text

    @property
    def artifacts_dir(self) -> str:
        """Get the appropriate artifacts directory based on configuration"""
        return self.S3_BUCKET if self.USE_S3 else self.LOCAL_ARTIFACTS_DIR

    @property
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return self.ENVIRONMENT == "production"


# Global settings instance
settings = Settings()
