"""Environment-based application settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings loaded from environment variables or a local .env file."""

    app_name: str = "Coach2Earn API"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://localhost:5432/coach2earn"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

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
