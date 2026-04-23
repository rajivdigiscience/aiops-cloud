from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Ops Hub"
    environment: str = "dev"
    command_timeout_seconds: int = 40

    enable_openai_enrichment: bool = True
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"

    require_api_key: bool = True
    api_keys_admin: str = "admin-dev-key"
    api_keys_operator: str = "operator-dev-key"
    api_keys_viewer: str = "viewer-dev-key"

    state_db_path: str = "./data/aiops_hub.db"
    cors_allow_origins: str = "*"

    model_config = SettingsConfigDict(env_file=".env", env_prefix="AIOPS_", extra="ignore")

    def ensure_state_dir(self) -> None:
        Path(self.state_db_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)

    def cors_origins(self) -> list[str]:
        return [value.strip() for value in self.cors_allow_origins.split(",") if value.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_state_dir()
    return settings
