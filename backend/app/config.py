from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///./data/app.db"
    chroma_path: str = "./data/chroma"
    # Aliases for common env names (pydantic-settings also accepts DATABASE_URL, etc.)
    jwt_secret: str = "change-me-in-production-use-long-random-string"
    jwt_cookie_name: str = "session"
    jwt_max_age_seconds: int = 86400 * 7
    llm_base_url: str = "https://api.groq.com/openai/v1"
    groq_api_key: str = ""
    llm_model: str = "llama-3.3-70b-versatile"
    huggingfacehub_api_token: str | None = None
    upload_max_bytes: int = 2 * 1024 * 1024
    chunk_size: int = 800
    chunk_overlap: int = 100
    policy_docs_dir: Path = Path(__file__).resolve().parents[2] / "policy_docs"
    data_dir: Path = Path("./data")


@lru_cache
def get_settings() -> Settings:
    return Settings()
