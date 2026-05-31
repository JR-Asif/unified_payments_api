from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_ENV: str = Field(default="development", description="Current execution environment profile")

    DATABASE_URL: str = Field(..., description="PostgreSQL connection string")

    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL (use 'redis://redis:6379/0' inside docker-compose).",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
