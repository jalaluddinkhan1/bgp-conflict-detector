"""
Application configuration using 12-factor app principles.
Uses Pydantic BaseSettings for environment variable management.
"""
from enum import Enum
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class OAuth2Provider(str, Enum):
    """Supported OAuth2 providers."""

    AZURE = "azure"
    GOOGLE = "google"
    OKTA = "okta"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database Configuration
    DATABASE_URL: str = Field(
        ...,
        description="PostgreSQL database connection URL",
        examples=["postgresql://user:password@localhost:5432/bgp_orchestrator"],
    )
    DATABASE_POOL_SIZE: int = Field(default=20, ge=1, le=100, description="Base connection pool size")
    DATABASE_MAX_OVERFLOW: int = Field(default=10, ge=0, description="Emergency connections beyond pool_size")
    DATABASE_POOL_TIMEOUT: int = Field(default=30, ge=1, description="Seconds to wait for connection before failing")
    DATABASE_POOL_PRE_PING: bool = Field(default=True, description="Detect stale connections before use")

    # Redis Configuration
    REDIS_URL: str = Field(
        ...,
        description="Redis connection URL",
        examples=["redis://localhost:6379/0"],
    )
    REDIS_MAX_CONNECTIONS: int = Field(default=50, ge=1)

    # Security Configuration
    SECRET_KEY: str = Field(
        ...,
        min_length=32,
        description="Secret key for cryptographic operations",
    )
    ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    JWT_SECRET_KEY: str | None = Field(default=None, description="JWT secret key (falls back to SECRET_KEY)")
    JWT_EXPIRATION_HOURS: int = Field(default=24, ge=1)

    # OAuth2 Configuration
    OAUTH2_PROVIDER: OAuth2Provider | None = Field(
        default=None,
        description="OAuth2 provider (azure/google/okta)",
    )
    OAUTH2_CLIENT_ID: str | None = None
    OAUTH2_CLIENT_SECRET: str | None = None
    OAUTH2_TENANT_ID: str | None = None  # For Azure AD
    OAUTH2_REDIRECT_URI: str | None = Field(
        default=None,
        description="OAuth2 redirect URI for callback (e.g., http://localhost:8000/api/v1/auth/callback)",
    )

    # External Service Endpoints
    BATFISH_ENDPOINT: str | None = Field(
        default=None,
        description="Batfish network analysis endpoint",
        examples=["http://batfish:9996"],
    )
    SUZIEQ_ENDPOINT: str | None = Field(
        default=None,
        description="SuzieQ network observability endpoint",
        examples=["http://suzieq:8000"],
    )

    # RIPE RIS Configuration
    RIPE_RIS_ENABLED: bool = Field(default=False, description="Enable RIPE RIS integration")
    RIPE_RIS_ENDPOINT: str = Field(
        default="https://ris-live.ripe.net/v1/json",
        description="RIPE RIS API endpoint",
    )

    # API Configuration
    API_HOST: str = Field(default="0.0.0.0")
    API_PORT: int = Field(default=8000, ge=1, le=65535)
    API_PREFIX: str = Field(default="/api/v1")
    CORS_ORIGINS: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:5173"],
        description="Allowed CORS origins",
    )

    # Logging Configuration
    LOG_LEVEL: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    LOG_FORMAT: str = Field(default="json", pattern="^(json|text)$")

    # Observability
    PROMETHEUS_PORT: int = Field(default=9090, ge=1, le=65535)
    JAEGER_ENABLED: bool = Field(default=False)
    JAEGER_HOST: str = Field(default="localhost")
    JAEGER_PORT: int = Field(default=6831, ge=1, le=65535)
    
    # VictoriaMetrics Configuration (optional, for long-term storage)
    VICTORIAMETRICS_ENABLED: bool = Field(default=False, description="Enable VictoriaMetrics integration")
    VICTORIAMETRICS_URL: str | None = Field(
        default=None,
        description="VictoriaMetrics base URL (e.g., http://victoriametrics:8428)",
        examples=["http://victoriametrics:8428"],
    )
    
    # Pyroscope Configuration (optional, for continuous profiling)
    PYROSCOPE_ENABLED: bool = Field(default=False, description="Enable Pyroscope profiling")
    PYROSCOPE_URL: str | None = Field(
        default=None,
        description="Pyroscope server URL (e.g., http://pyroscope:4040)",
        examples=["http://pyroscope:4040"],
    )
    
    # Kafka Configuration (for streaming BGP updates)
    KAFKA_ENABLED: bool = Field(default=False, description="Enable Kafka streaming")
    KAFKA_BOOTSTRAP_SERVERS: str | None = Field(
        default=None,
        description="Kafka bootstrap servers (comma-separated)",
        examples=["localhost:9092", "kafka1:9092,kafka2:9092"],
    )
    KAFKA_TOPICS: str | None = Field(
        default=None,
        description="Kafka topics to subscribe to (comma-separated)",
        examples=["ripe-ris-updates", "bgp-updates"],
    )
    KAFKA_GROUP_ID: str = Field(
        default="bgp-orchestrator-consumer",
        description="Kafka consumer group ID",
    )
    
    # Feature Store Configuration
    FEATURE_STORE_ENABLED: bool = Field(default=False, description="Enable Feast feature store")
    FEATURE_STORE_REPO_PATH: str | None = Field(
        default=None,
        description="Path to Feast feature store repository",
        examples=["./ml/feature_store"],
    )
    
    # Incident Management (Grafana OnCall)
    ONCALL_ENABLED: bool = Field(default=False, description="Enable Grafana OnCall integration")
    ONCALL_URL: str | None = Field(
        default=None,
        description="Grafana OnCall base URL",
        examples=["http://oncall:8080"],
    )
    ONCALL_API_TOKEN: str | None = Field(
        default=None,
        description="Grafana OnCall API token",
    )
    ONCALL_SCHEDULE_NAME: str = Field(
        default="bgp-orchestrator-oncall",
        description="On-call schedule name",
    )
    
    # Slack Integration
    SLACK_WEBHOOK_URL: str | None = Field(
        default=None,
        description="Slack webhook URL for #noc-alerts channel",
    )

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Validate secret key meets minimum security requirements."""
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate database URL format."""
        if not v.startswith(("postgresql://", "postgresql+psycopg2://")):
            raise ValueError("DATABASE_URL must be a PostgreSQL connection string")
        return v

    @field_validator("REDIS_URL")
    @classmethod
    def validate_redis_url(cls, v: str) -> str:
        """Validate Redis URL format."""
        if not v.startswith(("redis://", "rediss://")):
            raise ValueError("REDIS_URL must be a Redis connection string")
        return v

    @property
    def jwt_secret(self) -> str:
        """Get JWT secret key, falling back to SECRET_KEY if not set."""
        return self.JWT_SECRET_KEY or self.SECRET_KEY


# Global settings instance
settings = Settings()

