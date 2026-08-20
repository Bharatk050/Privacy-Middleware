from functools import lru_cache

from pydantic import Field, HttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. Secrets are read only from the environment."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    model_base_url: HttpUrl | None = Field(default=None, description="Optional provider API base URL")
    model_api_key: str = ""
    model_name: str = Field(min_length=1)
    model_timeout_seconds: float = Field(default=30, gt=0, le=300)
    session_ttl_seconds: int = Field(default=900, ge=60, le=86_400)
    log_level: str = "INFO"
    log_file: str = "logs/middleware.log"
    log_max_bytes: int = Field(default=5_000_000, ge=100_000)
    log_backup_count: int = Field(default=3, ge=1, le=20)

    @field_validator("model_base_url", mode="before")
    @classmethod
    def blank_model_base_url_is_none(cls, value: object) -> object:
        return None if isinstance(value, str) and not value.strip() else value


@lru_cache
def get_settings() -> Settings:
    return Settings()
