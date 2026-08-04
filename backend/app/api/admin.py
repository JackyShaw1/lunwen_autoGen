from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user, load_agent_yaml_files, require_admin
from app.models import AgentConfig, User
from app.schemas import AgentConfigOut, AgentConfigUpdate

router = APIRouter(prefix="/admin", tags=["admin"])

AGENT_ORDER = [
    "CasePlanner",
    "DomainExpert",
    "CaseWriter",
    "PedagogyDesigner",
    "Reviewer",
]


def _parse_meta(config_yaml: str, agent_name: str) -> dict:
    desc = f"Agent {agent_name}"
    role = ""
    model = ""
    for line in (config_yaml or "").splitlines():
        if line.startswith("description:"):
            desc = line.split(":", 1)[1].strip().strip('"').strip("'")
        elif line.startswith("role:"):
            role = line.split(":", 1)[1].strip().strip('"').strip("'")
            if desc.startswith("Agent "):
                desc = role
    lines = (config_yaml or "").splitlines()
    in_model = False
    for line in lines:
        if line.startswith("model:"):
            in_model = True
            continue
        if in_model:
            if line.startswith(" ") or line.startswith("\t"):
                if "name:" in line:
                    model = line.split(":", 1)[1].strip()
            else:
                in_model = False
    return {"description": role or desc, "model": model}


def _sorted_agents(items: list[AgentConfigOut]) -> list[AgentConfigOut]:
    order = {n: i for i, n in enumerate(AGENT_ORDER)}
    return sorted(items, key=lambda a: order.get(a.agent_name, 99))


@router.get("/agents", response_model=list[AgentConfigOut])
def list_agents(db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    """任意登录用户可查看 Agent 列表。"""
    db_configs = (
        db.query(AgentConfig)
        .filter(AgentConfig.is_active == True)  # noqa: E712
        .all()
    )
    if db_configs:
        # 每个 agent_name 只取最新一条
        latest: dict[str, AgentConfig] = {}
        for c in db_configs:
            prev = latest.get(c.agent_name)
            if not prev or (c.created_at and prev.created_at and c.created_at > prev.created_at):
                latest[c.agent_name] = c
        out = []
        for c in latest.values():
            meta = _parse_meta(c.config_yaml, c.agent_name)
            out.append(
                AgentConfigOut(
                    agent_name=c.agent_name,
                    version=c.version,
                    is_active=c.is_active,
                    description=meta["description"],
                )
            )
        return _sorted_agents(out)

    files = load_agent_yaml_files(settings.agents_dir)
    return _sorted_agents(
        [
            AgentConfigOut(
                agent_name=f["agent_name"],
                version=f["version"],
                is_active=f["is_active"],
                description=f.get("description"),
            )
            for f in files
        ]
    )


@router.get("/agents/{name}")
def get_agent_config(name: str, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    """任意登录用户可查看 YAML。"""
    cfg = (
        db.query(AgentConfig)
        .filter(AgentConfig.agent_name == name, AgentConfig.is_active == True)  # noqa: E712
        .order_by(AgentConfig.created_at.desc())
        .first()
    )
    if cfg:
        return {"agent_name": name, "version": cfg.version, "config_yaml": cfg.config_yaml}
    files = load_agent_yaml_files(settings.agents_dir)
    for f in files:
        if f["agent_name"] == name:
            return {"agent_name": name, "version": f["version"], "config_yaml": f["config_yaml"]}
    raise HTTPException(404, "Agent 配置不存在")


@router.put("/agents/{name}")
def update_agent_config(
    name: str,
    body: AgentConfigUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """仅管理员可修改。"""
    db.query(AgentConfig).filter(AgentConfig.agent_name == name).update({"is_active": False})
    version = "1.0.0"
    for line in body.config_yaml.splitlines():
        if line.startswith("version:"):
            version = line.split(":", 1)[1].strip().strip('"').strip("'")
            break
    cfg = AgentConfig(
        agent_name=name,
        version=version,
        config_yaml=body.config_yaml,
        is_active=body.activate,
    )
    db.add(cfg)
    db.commit()
    return {"message": "配置已更新", "agent_name": name, "version": version}
