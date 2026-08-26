"""管理员可在线更新的 OpenAI 兼容模型配置。"""

from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import SessionLocal
from app.models import SystemMeta

MODEL_CONFIG_KEY = "runtime-model-config-v1"
MODEL_API_KEY = "runtime-model-api-key-v1"


@dataclass(frozen=True)
class ActiveModelConfig:
    enabled: bool
    api_base: str
    model: str
    api_key: str
    source: str

    @property
    def available(self) -> bool:
        return self.enabled and bool(self.api_key.strip()) and bool(self.model.strip())


def _fernet() -> Fernet:
    secret = get_settings().secret_key.encode("utf-8")
    key = base64.urlsafe_b64encode(hashlib.sha256(secret).digest())
    return Fernet(key)


def encrypt_api_key(value: str) -> str:
    return _fernet().encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_api_key(value: str) -> str:
    if not value:
        return ""
    try:
        return _fernet().decrypt(value.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError):
        return ""


def _read_admin_config(db: Session) -> tuple[dict | None, str]:
    config_row = db.get(SystemMeta, MODEL_CONFIG_KEY)
    if not config_row:
        return None, ""
    try:
        config = json.loads(config_row.value)
    except (TypeError, json.JSONDecodeError):
        config = {}
    key_row = db.get(SystemMeta, MODEL_API_KEY)
    return config, decrypt_api_key(key_row.value if key_row else "")


def get_active_model_config(db: Session | None = None) -> ActiveModelConfig:
    owns_session = db is None
    session = db or SessionLocal()
    try:
        admin_config, admin_key = _read_admin_config(session)
    finally:
        if owns_session:
            session.close()

    if admin_config is not None:
        return ActiveModelConfig(
            enabled=bool(admin_config.get("enabled")),
            api_base=str(admin_config.get("api_base") or "https://api.openai.com/v1").rstrip("/"),
            model=str(admin_config.get("model") or "").strip(),
            api_key=admin_key,
            source="admin",
        )

    settings = get_settings()
    return ActiveModelConfig(
        enabled=not settings.use_mock_generation,
        api_base=settings.openai_api_base.rstrip("/"),
        model=settings.openai_model.strip(),
        api_key=settings.openai_api_key.strip(),
        source="environment" if settings.openai_api_key.strip() else "none",
    )


def get_masked_model_config(db: Session) -> dict:
    active = get_active_model_config(db)
    return {
        "enabled": active.enabled,
        "api_base": active.api_base,
        "model": active.model,
        "api_key_configured": bool(active.api_key),
        "api_key_masked": "••••••••" if active.api_key else "",
        "available": active.available,
        "source": active.source,
    }


def save_model_config(
    db: Session,
    *,
    enabled: bool,
    api_base: str,
    model: str,
    api_key: str | None,
    clear_api_key: bool = False,
) -> dict:
    payload = json.dumps(
        {"enabled": enabled, "api_base": api_base.rstrip("/"), "model": model.strip()},
        ensure_ascii=False,
        separators=(",", ":"),
    )
    config_row = db.get(SystemMeta, MODEL_CONFIG_KEY)
    if config_row:
        config_row.value = payload
    else:
        db.add(SystemMeta(key=MODEL_CONFIG_KEY, value=payload))

    key_row = db.get(SystemMeta, MODEL_API_KEY)
    if clear_api_key:
        if key_row:
            db.delete(key_row)
    elif api_key is not None and api_key.strip():
        encrypted = encrypt_api_key(api_key.strip())
        if key_row:
            key_row.value = encrypted
        else:
            db.add(SystemMeta(key=MODEL_API_KEY, value=encrypted))
    db.commit()
    return get_masked_model_config(db)
