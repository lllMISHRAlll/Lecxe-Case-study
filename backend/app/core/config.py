"""Application settings, read from the environment and the project `.env` file."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_env: Literal["dev", "test", "prod"] = "dev"

    # Databases
    database_url: SecretStr = SecretStr("")
    database_sslmode: str = "require"
    test_database_url: str = "postgresql://postgres:postgres@localhost:55432/postgres"
    statement_timeout_ms: int = 5000
    row_cap: int = 500
    explain_cost_limit: float = 1_000_000.0

    # LLM: LLM_PROVIDER picks which backend is used; FAKE_LLM forces the offline one.
    llm_provider: Literal["openai", "anthropic"] = "openai"
    openai_api_key: SecretStr = SecretStr("")
    openai_model_fast: str = "gpt-4o-mini"
    openai_model_sql: str = "gpt-4o"
    anthropic_api_key: SecretStr = SecretStr("")
    anthropic_model_fast: str = "claude-haiku-5-5"
    anthropic_model_strong: str = "claude-sonnet-5-5"
    fake_llm: bool = False

    # Auth
    jwt_secret: SecretStr = SecretStr("dev-only-change-me-0123456789abcdef")
    jwt_ttl_hours: int = 8
    cookie_name: str = "pa_session"
    demo_login_password: SecretStr | None = None  # shown on quick-login buttons outside prod

    # Business rules
    fx_usd_inr: float = Field(default=88.0, gt=0)

    # Limits
    rate_limit_per_minute: int = 20
    rate_limit_per_day: int = 300
    login_rate_limit_per_minute: int = 10

    # Observability
    langsmith_tracing: bool = False
    langsmith_api_key: SecretStr = SecretStr("")
    langsmith_project: str = "procurement-assistant"
    langsmith_endpoint: str | None = None

    @property
    def cookie_secure(self) -> bool:
        return self.app_env == "prod"

    @property
    def tracing_enabled(self) -> bool:
        return self.langsmith_tracing and bool(self.langsmith_api_key.get_secret_value())


@lru_cache
def get_settings() -> Settings:
    return Settings()
