"""管理员配置的自动事实研究服务。"""

from __future__ import annotations

import json
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import SystemMeta
from app.services.runtime_model_service import decrypt_api_key, encrypt_api_key

RESEARCH_CONFIG_KEY = "runtime-research-config-v1"
RESEARCH_API_KEY = "runtime-research-api-key-v1"


@dataclass(frozen=True)
class ResearchConfig:
    enabled: bool
    provider: str
    api_key: str

    @property
    def available(self) -> bool:
        return self.enabled and self.provider == "tavily" and bool(self.api_key)


def get_research_config(db: Session | None = None) -> ResearchConfig:
    owns = db is None
    session = db or SessionLocal()
    try:
        row = session.get(SystemMeta, RESEARCH_CONFIG_KEY)
        key_row = session.get(SystemMeta, RESEARCH_API_KEY)
        try:
            payload = json.loads(row.value) if row else {}
        except (TypeError, json.JSONDecodeError):
            payload = {}
        return ResearchConfig(
            enabled=bool(payload.get("enabled")),
            provider=str(payload.get("provider") or "tavily"),
            api_key=decrypt_api_key(key_row.value if key_row else ""),
        )
    finally:
        if owns:
            session.close()


def masked_research_config(db: Session) -> dict:
    config = get_research_config(db)
    return {
        "enabled": config.enabled,
        "provider": config.provider,
        "api_key_configured": bool(config.api_key),
        "api_key_masked": "••••••••" if config.api_key else "",
        "available": config.available,
    }


def save_research_config(db: Session, *, enabled: bool, provider: str, api_key: str | None) -> dict:
    payload = json.dumps({"enabled": enabled, "provider": provider}, separators=(",", ":"))
    row = db.get(SystemMeta, RESEARCH_CONFIG_KEY)
    if row:
        row.value = payload
    else:
        db.add(SystemMeta(key=RESEARCH_CONFIG_KEY, value=payload))
    if api_key and api_key.strip():
        encrypted = encrypt_api_key(api_key.strip())
        key_row = db.get(SystemMeta, RESEARCH_API_KEY)
        if key_row:
            key_row.value = encrypted
        else:
            db.add(SystemMeta(key=RESEARCH_API_KEY, value=encrypted))
    db.commit()
    return masked_research_config(db)
