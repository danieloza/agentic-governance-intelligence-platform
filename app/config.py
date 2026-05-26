from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Agentic Governance Intelligence Platform"
    environment: str = "development"
    demo_seed_enabled: bool = True
    database_url: str = "sqlite:///./agentic_governance_intelligence.db"
    jwt_secret: str = Field(default="dev-only-change-me-32-byte-minimum-key", min_length=32)
    jwt_algorithm: str = "HS256"
    token_expiry_minutes_default: int = 60
    policy_version: str = "2026.05.25"
    redact_full_name: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
