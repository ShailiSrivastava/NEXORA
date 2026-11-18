
from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    project_name: str = Field(default="NEXORA")
    api_v1_str: str = Field(default="/api/v1")
    app_version: str = Field(default="0.1.0")

    environment: str = Field(default="development")
    debug: bool = Field(default=False)
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)

    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/nexora"
    )

    redis_url: str = Field(default="redis://localhost:6379/0")
    redis_ttl_seconds: int = Field(default=3600)

    # AI provider configuration
    ai_provider: Literal["gemini", "ollama"] = Field(default="gemini")

    gemini_api_key: str = Field(default="")
    gemini_model: str = Field(default="gemini-2.5-flash")

    ollama_base_url: str = Field(default="http://localhost:11434")
    ollama_model: str = Field(default="qwen2.5:3b")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
