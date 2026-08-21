import asyncio
from datetime import datetime, timezone
from pathlib import Path

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
    ObjectiveSuggestionRequest,
    ObjectiveSuggestionResponse,
    PptOutlineRequest,
)
from app.services.export_service import export_docx, export_pdf
from app.services.orchestrator import consume_quota, run_generation
from app.services.objective_generator import generate_objectives
from app.services.package_builder import normalize_case_package
from app.services.pptx_export_service import build_ppt_outline, export_pptx, outline_preview
from app.services.progress_hub import progress_hub
from app.services.skill_loader import validate_package_with_skill

router = APIRouter(prefix="/cases", tags=["cases"])

# 防止 create_task 被 GC 提前回收
_bg_tasks: set[asyncio.Task] = set()


def _task_context(task: CaseTask) -> dict:
    return {
        "title": task.title,
        "subject": task.subject,
        "course_name": task.course_name,
        "case_type": task.case_type,
        "difficulty": task.difficulty,
        "target_audience": task.target_audience,
        "target_words": task.target_words,
        "learning_objectives": task.learning_objectives or [],
        "workflow_template": task.workflow_template,
        "config": task.config or {},
    }


async def _run_generation_task(task_id: str) -> None:
    """在主事件循环中跑生成，确保 WebSocket 进度推送可用。"""
    db = SessionLocal()
    try:
        await run_generation(db, task_id)
    finally:
        db.close()


def _spawn_generation(task_id: str) -> None:
    task = asyncio.create_task(_run_generation_task(task_id))
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


@router.post("/suggest-objectives", response_model=ObjectiveSuggestionResponse)
def suggest_objectives(
    body: ObjectiveSuggestionRequest,
    _user: User = Depends(get_current_user),
):
    """依据案例类型选择思维框架，每次返回三条可编辑的教学目标。"""
    return generate_objectives(body.model_dump())


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
    normalize_case_package(pkg.package)
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

    normalize_case_package(package)
    validation = validate_package_with_skill(package, _task_context(task))
    package.setdefault("quality", {})["validation"] = validation

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

    normalize_case_package(pkg.package)
    validation = validate_package_with_skill(pkg.package, _task_context(task))
    validation_errors = [
        issue["message"] for issue in validation["issues"] if issue.get("severity") == "error"
    ]
    if validation_errors:
        raise HTTPException(400, "导出前质量校验未通过：" + "；".join(validation_errors))

    try:
        if body.format == "docx":
            path = export_docx(pkg.package, task.title, pkg.version)
        elif body.format == "pdf":
            path = export_pdf(pkg.package, task.title, pkg.version)
        else:
            path = export_pptx(
                pkg.package,
                task.title,
                pkg.version,
                body.ppt_options.model_dump() if body.ppt_options else None,
            )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, f"{body.format.upper()} 导出失败：{exc}") from exc

    rec = ExportRecord(task_id=task_id, format=body.format, file_path=path)
    db.add(rec)
    db.commit()
    db.refresh(rec)

    return ExportResponse(
        export_id=rec.id,
        format=body.format,
        download_url=f"/api/cases/{task_id}/exports/{rec.id}/download",
        filename=Path(path).name,
        version=pkg.version,
    )


@router.post("/{task_id}/ppt-outline")
def preview_ppt_outline(
    task_id: str,
    body: PptOutlineRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = db.query(CaseTask).filter(CaseTask.id == task_id, CaseTask.user_id == user.id).first()
    if not task:
        raise HTTPException(404, "任务不存在")
    pkg = get_latest_package(task_id, db)
    if not pkg:
        raise HTTPException(400, "请先生成案例")
    normalize_case_package(pkg.package)
    return outline_preview(build_ppt_outline(pkg.package, body.model_dump()))


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
    media_types = {
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "pdf": "application/pdf",
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    }
    media = media_types.get(rec.format, "application/octet-stream")
    path = Path(rec.file_path)
    if not path.exists():
        raise HTTPException(404, "导出文件已不存在，请重新导出")
    return FileResponse(path, media_type=media, filename=path.name)
