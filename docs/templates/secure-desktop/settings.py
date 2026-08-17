"""Secure replacement for backend/app/config/settings.py in desktop builds.

The desktop launcher provisions JWT_SECRET_KEY before this module imports.
There is deliberately no default JWT secret and no automatic loading of a
working-directory `.env` file.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Aurora Relay API"
    app_version: str = "1.0.0"
    debug: bool = False
    api_v1_str: str = "/api/v1"

    cors_origins: list[str] = Field(default_factory=lambda: ["http://127.0.0.1", "http://localhost"])
    allowed_hosts: list[str] = Field(default_factory=lambda: ["localhost", "127.0.0.1"])

    # Required: runtime_secrets.load_runtime_secret() must set this before import.
    jwt_secret_key: str = Field(min_length=64, repr=False)
    jwt_algorithm: str = "HS256"
    access_token_expire_seconds: int = Field(default=3600, ge=60, le=86_400)

    database_url: str = "sqlite:///./data/api.db"
    database_pool_size: int = Field(default=10, ge=1, le=30)
    database_max_overflow: int = Field(default=20, ge=0, le=50)
    redis_url: str | None = None

    default_llm_provider: str = "local"
    llm_models: dict[str, str] = Field(
        default_factory=lambda: {
            "local": "phi3:mini",
            "openai": "gpt-4o-mini",
            "anthropic": "claude-3-5-sonnet-latest",
        }
    )
    mcp_servers_config: str = "backend/app/config/mcp_servers.json"
    mcp_connection_timeout: int = Field(default=30, ge=1, le=120)

    sandbox_enabled: bool = True
    sandbox_default_timeout: int = Field(default=30, ge=1, le=600)
    sandbox_memory_limit: str = "512m"
    sandbox_cpu_limit: float = Field(default=1.0, gt=0, le=16)

    rate_limit_requests: int = Field(default=100, ge=1, le=10_000)
    rate_limit_window: int = Field(default=60, ge=1, le=3600)
    admin_user_ids: list[str] = Field(default_factory=list)

    # Runtime config is placed into os.environ by the launcher. Do not search
    # the current working directory for a user-supplied .env file.
    model_config = SettingsConfigDict(case_sensitive=False, extra="ignore")

    @field_validator("cors_origins", "allowed_hosts", "admin_user_ids", mode="before")
    @classmethod
    def parse_csv(cls, value: Any) -> Any:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def sqlalchemy_url(self) -> str:
        return self.database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
