import secrets
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
    debug: bool = False
    backend_port: int = 8010
    # 未配置环境变量时每次进程启动生成随机密钥，避免使用可公开猜测的默认值。
    secret_key: str = secrets.token_urlsafe(48)
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    session_refresh_token_expire_hours: int = 12
    default_registration_quota: int = 30
    refresh_cookie_name: str = "case_autogen_refresh"
    cookie_secure: bool = True
    seed_demo_users: bool = False
    algorithm: str = "HS256"

    database_url: str = "sqlite:///./data/case_autogen.db"

    openai_api_key: str = ""
    openai_api_base: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o"
    use_mock_generation: bool = True
    searxng_url: str = "http://searxng:8080"

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
