from pathlib import Path

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.services.auth_service import decode_token

security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")
    user_id = decode_token(credentials.credentials)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="令牌无效")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")
    return user


def get_latest_package(task_id: str, db: Session):
    from app.models import CasePackage

    return (
        db.query(CasePackage)
        .filter(CasePackage.task_id == task_id)
        .order_by(CasePackage.version.desc())
        .first()
    )


def task_to_out(task, rubric: float | None = None) -> dict:
    from datetime import datetime

    def fmt(dt):
        if isinstance(dt, datetime):
            return dt.isoformat()
        return dt

    return {
        "id": task.id,
        "title": task.title,
        "subject": task.subject,
        "course_name": task.course_name,
        "case_type": task.case_type,
        "difficulty": task.difficulty,
        "target_audience": task.target_audience,
        "status": task.status,
        "workflow_template": task.workflow_template,
        "rubric_overall": rubric,
        "created_at": fmt(task.created_at),
        "updated_at": fmt(task.updated_at),
    }


def load_agent_yaml_files(agents_dir: str) -> list[dict]:
    base = Path(agents_dir)
    if not base.exists():
        return []
    results = []
    for f in sorted(base.glob("*.yaml")):
        content = f.read_text(encoding="utf-8")
        name = f.stem
        version = "1.0.0"
        for line in content.splitlines():
            if line.startswith("version:"):
                version = line.split(":", 1)[1].strip().strip('"').strip("'")
                break
        results.append(
            {
                "agent_name": name,
                "version": version,
                "is_active": True,
                "description": f"Agent {name}",
                "config_yaml": content,
            }
        )
    return results
