import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.dependencies import get_current_user, get_latest_package, task_to_out
from app.models import AgentRunLog, CasePackage, CaseTask, ExportRecord, User
from app.schemas import (
    CaseTaskOut,
    CreateCaseRequest,
    ExportRequest,
    ExportResponse,
    RegenerateRequest,
)
from app.services.export_service import export_docx, export_pdf
from app.services.orchestrator import consume_quota, run_generation
from app.services.progress_hub import progress_hub

router = APIRouter(prefix="/cases", tags=["cases"])

# 防止 create_task 被 GC 提前回收
_bg_tasks: set[asyncio.Task] = set()


async def _run_generation_task(task_id: str, only_agent: str | None = None) -> None:
    """在主事件循环中跑生成，确保 WebSocket 进度推送可用。"""
    db = SessionLocal()
    try:
        await run_generation(db, task_id, only_agent=only_agent)
    finally:
        db.close()


def _spawn_generation(task_id: str, only_agent: str | None = None) -> None:
    task = asyncio.create_task(_run_generation_task(task_id, only_agent))
    _bg_tasks.add(task)
    task.add_done_callback(_bg_tasks.discard)


@router.get("", response_model=list[CaseTaskOut])
def list_cases(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tasks = db.query(CaseTask).filter(CaseTask.user_id == user.id).order_by(CaseTask.updated_at.desc()).all()
    out = []
    for t in tasks:
        pkg = get_latest_package(t.id, db)
        rubric = float(pkg.rubric_overall) if pkg and pkg.rubric_overall else None
        out.append(task_to_out(t, rubric))
    return out


@router.get("/{task_id}", response_model=CaseTaskOut)
def get_case(
    task_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = db.query(CaseTask).filter(CaseTask.id == task_id, CaseTask.user_id == user.id).first()
    if not task:
        raise HTTPException(404, "任务不存在")
    pkg = get_latest_package(task_id, db)
    rubric = float(pkg.rubric_overall) if pkg and pkg.rubric_overall else None
    return task_to_out(task, rubric)


@router.post("", response_model=CaseTaskOut)
def create_case(
    body: CreateCaseRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 草稿创建不扣配额；配额在启动 generate 时检查与扣减
    config = {}
    if body.class_hours:
        config["class_hours"] = body.class_hours
    if body.special_requirements:
        config["special_requirements"] = body.special_requirements

    task = CaseTask(
        user_id=user.id,
        title=body.title,
        subject=body.subject,
        course_name=body.course_name,
        case_type=body.case_type,
        difficulty=body.difficulty,
        target_audience=body.target_audience,
        target_words=body.target_words,
        learning_objectives=body.learning_objectives,
        workflow_template=body.workflow_template,
        config=config,
        status="draft",
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task_to_out(task)


@router.post("/{task_id}/generate")
async def start_generate(
    task_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = db.query(CaseTask).filter(CaseTask.id == task_id, CaseTask.user_id == user.id).first()
    if not task:
        raise HTTPException(404, "任务不存在")
    if task.status == "running":
        raise HTTPException(400, "任务正在生成中")
    if user.quota_remaining is not None and user.quota_remaining <= 0 and task.status == "draft":
        raise HTTPException(400, "生成配额已用尽")

    if task.status == "draft":
        consume_quota(db, user)

    _spawn_generation(task_id, None)
    return {"message": "生成已启动", "task_id": task_id}


@router.get("/{task_id}/live")
def get_live_progress(
    task_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """前端轮询用：返回内存中最新进度（含 stream 打字文本）。"""
    task = db.query(CaseTask).filter(CaseTask.id == task_id, CaseTask.user_id == user.id).first()
    if not task:
        raise HTTPException(404, "任务不存在")
    state = progress_hub.get_state(task_id)
    if state:
        return state
    # 无内存进度时按任务状态兜底
    done = task.status in ("finalized", "completed")
    return {
        "type": "agent_progress",
        "task_id": task_id,
        "overall_progress": 100 if done else (1 if task.status == "running" else 0),
        "current_agent": None,
        "agents": [],
        "step_results": [],
        "task_meta": {"title": task.title, "subject": task.subject, "course_name": task.course_name},
        "status": task.status,
        "error_message": task.error_message,
    }


@router.get("/{task_id}/status")
def get_status(
    task_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = db.query(CaseTask).filter(CaseTask.id == task_id, CaseTask.user_id == user.id).first()
    if not task:
        raise HTTPException(404, "任务不存在")
    logs = (
        db.query(AgentRunLog)
        .filter(AgentRunLog.task_id == task_id)
        .order_by(AgentRunLog.created_at.asc())
        .all()
    )
    return {
        "task_id": task_id,
        "status": task.status,
        "error_message": task.error_message,
        "logs": [
            {
                "agent_name": l.agent_name,
                "output_summary": l.output_summary,
                "duration_ms": l.duration_ms,
                "token_usage": l.token_usage,
                "created_at": l.created_at.isoformat() if l.created_at else None,
            }
            for l in logs
        ],
    }


@router.get("/{task_id}/logs")
def get_logs(
    task_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = db.query(CaseTask).filter(CaseTask.id == task_id, CaseTask.user_id == user.id).first()
    if not task:
        raise HTTPException(404, "任务不存在")
    logs = (
        db.query(AgentRunLog)
        .filter(AgentRunLog.task_id == task_id)
        .order_by(AgentRunLog.created_at.desc())
        .all()
    )
    return [
        {
            "id": l.id,
            "agent_name": l.agent_name,
            "round": l.round,
            "input_summary": l.input_summary,
            "output_summary": l.output_summary,
            "token_usage": l.token_usage,
            "duration_ms": l.duration_ms,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }
        for l in logs
    ]


@router.get("/{task_id}/package")
def get_package(
    task_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = db.query(CaseTask).filter(CaseTask.id == task_id, CaseTask.user_id == user.id).first()
    if not task:
        raise HTTPException(404, "任务不存在")
    pkg = get_latest_package(task_id, db)
    if not pkg:
        raise HTTPException(404, "案例包尚未生成")
    return {
        "version": pkg.version,
        "status": pkg.status,
        "rubric_overall": float(pkg.rubric_overall) if pkg.rubric_overall else None,
        "package": pkg.package,
    }


@router.put("/{task_id}/package")
def update_package(
    task_id: str,
    body: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = db.query(CaseTask).filter(CaseTask.id == task_id, CaseTask.user_id == user.id).first()
    if not task:
        raise HTTPException(404, "任务不存在")

    # 兼容直接传 package 或 { package: ... }
    package = body.get("package") if isinstance(body.get("package"), dict) else body
    if not isinstance(package, dict) or "meta" not in package:
        raise HTTPException(400, "无效的案例包结构")

    pkg = get_latest_package(task_id, db)
    next_version = 1
    if pkg:
        next_version = (pkg.version or 1) + 1

    overall = None
    if package.get("quality", {}).get("overall_score") is not None:
        overall = package["quality"]["overall_score"]

    new_pkg = CasePackage(
        task_id=task_id,
        version=next_version,
        package=package,
        rubric_overall=overall,
        status="draft",
    )
    db.add(new_pkg)
    task.status = "completed"
    task.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "已保存", "version": next_version}


@router.post("/{task_id}/regenerate")
async def regenerate_agent(
    task_id: str,
    body: RegenerateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = db.query(CaseTask).filter(CaseTask.id == task_id, CaseTask.user_id == user.id).first()
    if not task:
        raise HTTPException(404, "任务不存在")
    if task.status == "running":
        raise HTTPException(400, "任务正在生成中")
    if not get_latest_package(task_id, db):
        raise HTTPException(400, "请先完成首次生成")

    _spawn_generation(task_id, body.agent)
    return {"message": f"已触发 {body.agent} 重新生成", "task_id": task_id, "agent": body.agent}


@router.post("/{task_id}/export", response_model=ExportResponse)
def export_case(
    task_id: str,
    body: ExportRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = db.query(CaseTask).filter(CaseTask.id == task_id, CaseTask.user_id == user.id).first()
    if not task:
        raise HTTPException(404, "任务不存在")
    pkg = get_latest_package(task_id, db)
    if not pkg:
        raise HTTPException(400, "请先生成案例")

    if body.format == "docx":
        path = export_docx(pkg.package, task.title)
    else:
        path = export_pdf(pkg.package, task.title)

    rec = ExportRecord(task_id=task_id, format=body.format, file_path=path)
    db.add(rec)
    db.commit()
    db.refresh(rec)

    return ExportResponse(
        export_id=rec.id,
        format=body.format,
        download_url=f"/api/cases/{task_id}/exports/{rec.id}/download",
    )


@router.get("/{task_id}/exports/{export_id}/download")
def download_export(
    task_id: str,
    export_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from fastapi.responses import FileResponse

    task = db.query(CaseTask).filter(CaseTask.id == task_id, CaseTask.user_id == user.id).first()
    if not task:
        raise HTTPException(404, "任务不存在")
    rec = db.query(ExportRecord).filter(ExportRecord.id == export_id, ExportRecord.task_id == task_id).first()
    if not rec:
        raise HTTPException(404, "导出记录不存在")
    media = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if rec.format == "pdf":
        media = "application/pdf"
    return FileResponse(rec.file_path, media_type=media, filename=f"{task.title}.{rec.format}")
