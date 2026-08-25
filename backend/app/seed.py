from pathlib import Path

from app.database import Base, engine, SessionLocal
from app.models import AgentConfig, CaseTask, SystemMeta, User
from app.services.auth_service import hash_password
from app.dependencies import load_agent_yaml_files
from app.config import settings


def _version_tuple(value: str) -> tuple[int, ...]:
    """宽容解析 1.2.3；非数字部分按 0 处理，避免启动同步中断。"""
    parts = []
    for part in str(value or "0").split("."):
        digits = "".join(char for char in part if char.isdigit())
        parts.append(int(digits or 0))
    return tuple((parts + [0, 0, 0])[:3])


def _sync_bundled_agent_configs(db) -> None:
    """仅当内置 YAML 版本更高时激活它，保留管理员创建的更新版本。"""
    for bundled in load_agent_yaml_files(settings.agents_dir):
        current = (
            db.query(AgentConfig)
            .filter(
                AgentConfig.agent_name == bundled["agent_name"],
                AgentConfig.is_active == True,  # noqa: E712
            )
            .order_by(AgentConfig.created_at.desc())
            .first()
        )
        if current and _version_tuple(current.version) >= _version_tuple(bundled["version"]):
            continue
        db.query(AgentConfig).filter(
            AgentConfig.agent_name == bundled["agent_name"]
        ).update({"is_active": False})
        db.add(
            AgentConfig(
                agent_name=bundled["agent_name"],
                version=bundled["version"],
                config_yaml=bundled["config_yaml"],
                is_active=True,
            )
        )


def _migrate_v30_registration_quotas(db) -> None:
    """把旧版 5 次试用升级为 30 次总额度；只迁移一次且保留已消耗次数。"""
    marker_key = "registration-quota-v30"
    if db.get(SystemMeta, marker_key):
        return

    legacy_users = (
        db.query(User)
        .filter(User.role == "teacher", User.quota_remaining <= 5)
        .all()
    )
    for user in legacy_users:
        consumed = (
            db.query(CaseTask)
            .filter(CaseTask.user_id == user.id, CaseTask.status != "draft")
            .count()
        )
        user.quota_remaining = max(user.quota_remaining, settings.default_registration_quota - consumed, 0)

    db.add(SystemMeta(key=marker_key, value=f"migrated_users={len(legacy_users)}"))


def init_db():
    data_dir = Path("./data")
    data_dir.mkdir(exist_ok=True)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        _migrate_v30_registration_quotas(db)
        if settings.seed_demo_users:
            if not db.query(User).filter(User.email == "teacher@university.edu.cn").first():
                db.add(
                    User(
                        email="teacher@university.edu.cn",
                        password_hash=hash_password("demo123"),
                        name="演示教师",
                        role="teacher",
                        quota_remaining=50,
                    )
                )
            if not db.query(User).filter(User.email == "admin@university.edu.cn").first():
                db.add(
                    User(
                        email="admin@university.edu.cn",
                        password_hash=hash_password("admin123"),
                        name="系统管理员",
                        role="admin",
                        quota_remaining=99,
                    )
                )
        _sync_bundled_agent_configs(db)
        db.commit()
    finally:
        db.close()
