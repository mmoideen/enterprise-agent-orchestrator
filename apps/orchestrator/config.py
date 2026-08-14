"""Application configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # Security
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

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


settings = Settings()
