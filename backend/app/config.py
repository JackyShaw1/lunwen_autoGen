from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "CaseAutoGenSystem"
    debug: bool = True
    secret_key: str = "change-me-in-production-use-long-random-string"
    access_token_expire_minutes: int = 60 * 24 * 7
    algorithm: str = "HS256"

    database_url: str = "sqlite:///./data/case_autogen.db"

    openai_api_key: str = ""
    openai_api_base: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o"
    use_mock_generation: bool = True

    reviewer_pass_threshold: float = 4.0
    hours_saved_per_case: int = 8

    export_dir: str = "./data/exports"
    agents_dir: str = ""

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    if not s.agents_dir:
        s.agents_dir = str(Path(__file__).resolve().parent / "agents")
    if s.openai_api_key and s.use_mock_generation is True:
        # 可通过环境变量 USE_MOCK_GENERATION=false 启用真实 LLM
        pass
    return s


settings = get_settings()
