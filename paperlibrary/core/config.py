from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    llm_provider: str = "anthropic"
    llm_api_key: str = ""
    llm_model: str = "claude-haiku-4-5"
    llm_base_url: str | None = None

    storage_path: Path = Path("./storage")
    max_text_chars: int = 60000
    extract_pages: int = 25
    port: int = 8000

    model_config = SettingsConfigDict(
        env_prefix="PAPERLIBRARY_",
        env_file=".env",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
