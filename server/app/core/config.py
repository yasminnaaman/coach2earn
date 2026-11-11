"""Environment-based application settings."""

from functools import lru_cache

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings loaded from environment variables or a local .env file."""

    app_name: str = "Coach2Earn API"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://localhost:5432/coach2earn"
    jwt_secret_key: SecretStr | None = None
    access_token_expire_minutes: int = 30
    jwt_issuer: str = "coach2earn"
    cors_origins: str = "https://coach2earn-web.onrender.com,http://localhost:5173,http://localhost:3000"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_production_requirements(self) -> "Settings":
        """Fail loudly on startup when required production vars are missing."""
        if self.environment == "production":
            if "localhost" in self.database_url or "127.0.0.1" in self.database_url:
                raise ValueError(
                    "DATABASE_URL must be set to a hosted database in production "
                    "(current value still points at localhost)"
                )
            if self.jwt_secret_key is None:
                raise ValueError(
                    "JWT_SECRET_KEY must be set in production"
                )
        return self

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret(cls, value: SecretStr | None) -> SecretStr | None:
        """Reject short and obviously low-entropy secrets without a fallback."""
        if value is None:
            return None
        raw = value.get_secret_value()
        lowered = raw.casefold()
        weak_markers = ("change_me", "changeme", "replace_me", "example", "password", "secret_key")
        if len(raw.encode("utf-8")) < 32 or len(set(raw)) < 12 or any(
            marker in lowered for marker in weak_markers
        ):
            raise ValueError(
                "JWT_SECRET_KEY must be a randomly generated secret of at least 32 bytes"
            )
        return value

    @field_validator("access_token_expire_minutes")
    @classmethod
    def validate_token_expiry(cls, value: int) -> int:
        if not 1 <= value <= 1440:
            raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES must be between 1 and 1440")
        return value

    @property
    def sqlalchemy_database_url(self) -> str:
        """Normalize common hosted PostgreSQL URLs for psycopg 3."""
        if self.database_url.startswith("postgres://"):
            return self.database_url.replace("postgres://", "postgresql+psycopg://", 1)
        if self.database_url.startswith("postgresql://"):
            return self.database_url.replace("postgresql://", "postgresql+psycopg://", 1)
        return self.database_url


@lru_cache
def get_settings() -> Settings:
    """Return cached settings so the app has one consistent configuration."""
    return Settings()
