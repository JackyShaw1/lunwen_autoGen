from pathlib import Path

from app.database import Base, engine, SessionLocal
from app.models import AgentConfig, User
from app.services.auth_service import hash_password
from app.dependencies import load_agent_yaml_files
from app.config import settings


def init_db():
    data_dir = Path("./data")
    data_dir.mkdir(exist_ok=True)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
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
        if db.query(AgentConfig).count() == 0:
            for f in load_agent_yaml_files(settings.agents_dir):
                db.add(
                    AgentConfig(
                        agent_name=f["agent_name"],
                        version=f["version"],
                        config_yaml=f["config_yaml"],
                        is_active=True,
                    )
                )
        db.commit()
    finally:
        db.close()
