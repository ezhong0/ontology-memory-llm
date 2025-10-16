"""Application settings using Pydantic BaseSettings.

All settings are loaded from environment variables with defaults.
"""
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Environment
    environment: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Application environment"
    )

    # API Configuration
    api_host: str = Field(default="0.0.0.0", description="API host address")
    api_port: int = Field(default=8000, description="API port")
    api_reload: bool = Field(default=True, description="Enable auto-reload (dev only)")

    # Database Configuration
    database_url: str = Field(
        default="postgresql+asyncpg://memoryuser:memorypass@localhost:5432/memorydb",
        description="PostgreSQL connection URL (async)"
    )
    db_echo: bool = Field(default=False, description="Echo SQL statements")
    db_pool_size: int = Field(default=10, description="Connection pool size")
    db_max_overflow: int = Field(default=20, description="Max overflow connections")

    # LLM Provider Configuration
    llm_provider: Literal["openai", "anthropic"] = Field(
        default="anthropic",
        description="LLM provider (openai or anthropic)"
    )

    # OpenAI Configuration
    openai_api_key: str = Field(default="", description="OpenAI API key")
    openai_embedding_model: str = Field(
        default="text-embedding-3-small",
        description="OpenAI embedding model"
    )
    openai_embedding_dimensions: int = Field(default=1536, description="Embedding dimensions")
    openai_llm_model: str = Field(
        default="gpt-4-turbo-preview",
        description="LLM model for extraction"
    )

    # Anthropic Configuration
    anthropic_api_key: str = Field(default="", description="Anthropic API key")
    anthropic_model: str = Field(
        default="claude-haiku-4-5-20251015",
        description="Anthropic Claude model"
    )

    # Redis Configuration (Phase 2)
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )
    redis_enabled: bool = Field(default=False, description="Enable Redis caching")

    # Security
    secret_key: str = Field(
        default="dev-secret-key-change-in-production",
        description="Secret key for JWT signing"
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_expiration_minutes: int = Field(default=1440, description="JWT expiration (24 hours)")

    # CORS
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="Allowed CORS origins"
    )

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level"
    )
    log_format: Literal["json", "text"] = Field(
        default="json",
        description="Log format (json for production)"
    )

    # Feature Flags
    enable_embedding_async: bool = Field(
        default=True,
        description="Generate embeddings asynchronously"
    )
    enable_conflict_detection: bool = Field(
        default=True,
        description="Detect and log memory conflicts"
    )
    enable_procedural_memory: bool = Field(
        default=False,
        description="Enable procedural memory extraction (Phase 2)"
    )

    # Demo Mode
    DEMO_MODE_ENABLED: bool = Field(
        default=False,
        description="Enable demo endpoints and features (development only)"
    )

    # Performance
    max_conversation_history: int = Field(
        default=50,
        description="Max conversation history length"
    )
    max_retrieval_candidates: int = Field(
        default=50,
        description="Max candidates for retrieval"
    )
    max_selected_memories: int = Field(
        default=15,
        description="Max memories to include in context"
    )
    max_context_tokens: int = Field(
        default=3000,
        description="Max tokens for memory context"
    )

    # Domain Database (External)
    domain_db_url: str = Field(
        default="postgresql+asyncpg://readonly:password@localhost:5432/domain",
        description="Domain database connection URL (read-only)"
    )
    domain_db_enabled: bool = Field(
        default=True,
        description="Enable domain database integration"
    )

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"

    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"
