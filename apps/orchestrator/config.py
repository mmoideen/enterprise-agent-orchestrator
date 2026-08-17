"""Application configuration."""

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_SECRET_KEY = "change-me-in-production"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql+psycopg://user:password@localhost:5432/enterprise_agents"
    database_pool_size: int = 20
    database_max_overflow: int = 10

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_max_connections: int = 50

    # Temporal
    temporal_host: str = "localhost:7233"
    temporal_namespace: str = "default"
    temporal_task_queue: str = "enterprise-agents"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = True
    api_workers: int = 1

    # Environment
    environment: str = "development"

    # Security
    secret_key: str = DEFAULT_SECRET_KEY
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Governance
    policy_config_path: str = "./config/policies.yaml"
    risk_score_threshold: float = 0.75
    pii_detection_enabled: bool = True

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    # Agent Runtime
    agent_execution_timeout_seconds: int = 300
    max_concurrent_agents: int = 10

    # MCP
    mcp_server_enabled: bool = True
    mcp_server_port: int = 8001

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        """Reject the placeholder signing key outside development."""
        if self.environment != "development" and self.secret_key == DEFAULT_SECRET_KEY:
            raise ValueError(
                "SECRET_KEY must be set to a cryptographically secure value "
                f"when ENVIRONMENT={self.environment}"
            )
        return self


settings = Settings()
