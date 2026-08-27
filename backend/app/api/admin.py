import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user, load_agent_yaml_files, require_admin
from app.models import AgentConfig, User
from app.schemas import AgentConfigOut, AgentConfigUpdate, ModelConfigOut, ModelConfigUpdate, ResearchConfigOut, ResearchConfigUpdate
from app.services.runtime_model_service import (
    get_active_model_config,
    get_masked_model_config,
    save_model_config,
)
from app.services.runtime_research_service import get_research_config, masked_research_config, save_research_config

router = APIRouter(prefix="/admin", tags=["admin"])

AGENT_ORDER = [
    "CasePlanner",
    "DomainExpert",
    "CaseWriter",
    "PedagogyDesigner",
    "Reviewer",
]


@router.get("/research-config", response_model=ResearchConfigOut)
def read_research_config(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    return masked_research_config(db)


@router.put("/research-config", response_model=ResearchConfigOut)
def update_research_config(body: ResearchConfigUpdate, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    return save_research_config(db, enabled=body.enabled, provider=body.provider, api_key=body.api_key)


@router.post("/research-config/test")
async def test_research_config(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    config = get_research_config(db)
    if not config.api_key:
        raise HTTPException(400, "请先保存自动研究 API Key")
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                "https://api.tavily.com/search",
                headers={"Authorization": f"Bearer {config.api_key}", "Content-Type": "application/json"},
                json={"query": "中国 教育 官方", "max_results": 1, "search_depth": "basic"},
            )
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"自动研究服务连接失败：{type(exc).__name__}") from None
    if response.status_code >= 400:
        raise HTTPException(response.status_code, f"自动研究服务返回 HTTP {response.status_code}")
    return {"success": True, "message": "自动研究服务连接成功"}


@router.get("/model-config", response_model=ModelConfigOut)
def read_model_config(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """仅返回掩码状态，API Key 明文永不离开服务端。"""
    return get_masked_model_config(db)


@router.put("/model-config", response_model=ModelConfigOut)
def update_model_config(
    body: ModelConfigUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    return save_model_config(
        db,
        enabled=body.enabled,
        api_base=body.api_base,
        model=body.model,
        api_key=body.api_key,
        clear_api_key=body.clear_api_key,
    )


@router.post("/model-config/test")
async def test_model_config(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    config = get_active_model_config(db)
    if not config.api_key or not config.model:
        raise HTTPException(400, "请先保存模型名和 API Key")
    url = f"{config.api_base.rstrip('/')}/chat/completions"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                headers={"Authorization": f"Bearer {config.api_key}", "Content-Type": "application/json"},
                json={
                    "model": config.model,
                    "messages": [{"role": "user", "content": "请只回复：连接成功"}],
                    "temperature": 0,
                    "max_tokens": 16,
                },
            )
        if response.status_code >= 400:
            raise HTTPException(response.status_code, f"模型服务返回 HTTP {response.status_code}，请核对地址、模型名和密钥")
        data = response.json()
        if not (data.get("choices") or []):
            raise HTTPException(502, "模型服务已响应，但返回格式不是 OpenAI Chat Completions 格式")
    except HTTPException:
        raise
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(502, f"连接模型服务失败：{type(exc).__name__}") from None
    return {"success": True, "message": "连接成功", "model": config.model}


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
