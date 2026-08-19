from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = Field(default="SupportOps AI", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")

    # Ollama (local LLM) settings
    ollama_base_url: str = Field(default="http://localhost:11434/v1", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="qwen3", alias="OLLAMA_MODEL")


@lru_cache()
def get_settings() -> Settings:
    """Return a cached Settings singleton."""
    return Settings()


settings = get_settings()
