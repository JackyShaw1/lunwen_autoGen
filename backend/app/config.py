from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

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


def get_settings() -> Settings:
    """每次从绝对路径 .env 读取最新配置。"""
    s = Settings()
    if not s.agents_dir:
        s.agents_dir = str(Path(__file__).resolve().parent / "agents")
    return s


class _SettingsProxy:
    """属性访问时动态读 .env，避免进程内缓存导致一直走 Mock。"""

    def __getattr__(self, name: str):
        return getattr(get_settings(), name)


settings = _SettingsProxy()
