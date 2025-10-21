"""Application configuration management.

This module uses Pydantic Settings for environment-based configuration
following the 12-factor app principles. Configuration values are loaded
from environment variables with sensible defaults.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Attributes:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
                   Controls verbosity of application logs.
                   DEBUG: All logs (development)
                   INFO: Informational logs (staging)
                   WARNING: Only warnings/errors (production)
        debug: Debug mode flag (default: False)
               When True, exposes technical error details in API responses.
               When False (production), only shows user-friendly messages.
        DATABASE_URL: Async PostgreSQL connection string (asyncpg driver)
                      Format: postgresql+asyncpg://user:password@host:port/db
                      Used by application for async database operations.
        DATABASE_URL_SYNC: Sync PostgreSQL connection string (psycopg2 driver)
                           Format: postgresql+psycopg2://user:password@host:port/db
                           Used by Alembic for database migrations (migrations are sync).
        DB_POOL_SIZE: Base connection pool size (default: 20)
                      Number of persistent connections maintained in the pool.
        DB_MAX_OVERFLOW: Maximum overflow connections (default: 10)
                         Emergency connections beyond pool_size.
                         Total max connections = pool_size + max_overflow.
        DB_ECHO_SQL: Enable SQL query logging (default: False)
                     When True, logs all SQL queries to stdout.
                     Use only in DEBUG mode for development.
        AUTH0_DOMAIN: Auth0 tenant domain (e.g., demeter.us.auth0.com)
                      Used to construct JWKS endpoint and validate issuer.
        AUTH0_API_AUDIENCE: API identifier registered in Auth0 dashboard
                            Used to validate JWT audience claim.
        AUTH0_ALGORITHMS: List of allowed JWT algorithms (default: ["RS256"])
                          Auth0 uses RS256 (RSA signature with SHA-256).
    """

    # Logging configuration
    log_level: str = "INFO"

    # Debug mode (controls exception detail exposure)
    debug: bool = False

    # Database configuration
    DATABASE_URL: str = "postgresql+asyncpg://demeter:password@localhost:5432/demeterai"
    DATABASE_URL_SYNC: str = "postgresql+psycopg2://demeter:password@localhost:5432/demeterai"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_ECHO_SQL: bool = False

    # S3 configuration
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    S3_BUCKET_ORIGINAL: str = "demeter-photos-original"
    S3_BUCKET_VISUALIZATION: str = "demeter-photos-viz"
    S3_PRESIGNED_URL_EXPIRY_HOURS: int = 24

    # Auth0 configuration
    AUTH0_DOMAIN: str = ""  # Example: demeter.us.auth0.com
    AUTH0_API_AUDIENCE: str = ""  # Example: https://api.demeter.ai
    AUTH0_ALGORITHMS: list[str] = ["RS256"]

    @property
    def AUTH0_ISSUER(self) -> str:
        """Derived Auth0 issuer URL from domain.

        Returns:
            Issuer URL (e.g., https://demeter.us.auth0.com/)
        """
        if not self.AUTH0_DOMAIN:
            return ""
        domain = self.AUTH0_DOMAIN.replace("https://", "").replace("http://", "")
        return f"https://{domain}/"

    # OpenTelemetry configuration
    OTEL_ENABLED: bool = True
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4318"
    OTEL_SERVICE_NAME: str = "demeterai-api"
    APP_ENV: str = "development"

    # Metrics configuration
    ENABLE_METRICS: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


# Singleton settings instance
settings = Settings()
