from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import load_agent_yaml_files, require_admin
from app.models import AgentConfig
from app.schemas import AgentConfigOut, AgentConfigUpdate

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/agents", response_model=list[AgentConfigOut])
def list_agents(db: Session = Depends(get_db), _admin=Depends(require_admin)):
    db_configs = db.query(AgentConfig).filter(AgentConfig.is_active == True).all()
    if db_configs:
        return [
            AgentConfigOut(
                agent_name=c.agent_name,
                version=c.version,
                is_active=c.is_active,
                description=f"Agent {c.agent_name}",
            )
            for c in db_configs
        ]
    files = load_agent_yaml_files(settings.agents_dir)
    return [
        AgentConfigOut(
            agent_name=f["agent_name"],
            version=f["version"],
            is_active=f["is_active"],
            description=f.get("description"),
        )
        for f in files
    ]


@router.get("/agents/{name}")
def get_agent_config(name: str, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    cfg = (
        db.query(AgentConfig)
        .filter(AgentConfig.agent_name == name, AgentConfig.is_active == True)
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
    _admin=Depends(require_admin),
):
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
