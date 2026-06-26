import asyncio
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db, SessionLocal
from app.dependencies import get_current_user, get_latest_package, task_to_out
from app.models import AgentRunLog, CasePackage, CaseTask, ExportRecord, User
from app.schemas import CreateCaseRequest, CaseTaskOut, DashboardStatsOut, ExportRequest, ExportResponse, RegenerateRequest
from app.services.export_service import export_docx, export_pdf
from app.services.orchestrator import run_generation

router = APIRouter(prefix="/cases", tags=["cases"])


def _run_generation_bg(task_id: str):
    db = SessionLocal()
    try:
        asyncio.run(run_generation(db, task_id))
    finally:
        db.close()


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


@router.post("", response_model=CaseTaskOut)
def create_case(
    body: CreateCaseRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
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
def start_generate(
    task_id: str,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = db.query(CaseTask).filter(CaseTask.id == task_id, CaseTask.user_id == user.id).first()
    if not task:
        raise HTTPException(404, "任务不存在")
    if task.status == "running":
        raise HTTPException(400, "任务正在生成中")
    background_tasks.add_task(_run_generation_bg, task_id)
    return {"message": "生成已启动", "task_id": task_id}


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
    return pkg.package


@router.put("/{task_id}/package")
def update_package(
    task_id: str,
    package: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = db.query(CaseTask).filter(CaseTask.id == task_id, CaseTask.user_id == user.id).first()
    if not task:
        raise HTTPException(404, "任务不存在")
    pkg = get_latest_package(task_id, db)
    if not pkg:
        pkg = CasePackage(task_id=task_id, version=1, package=package)
        db.add(pkg)
    else:
        pkg.package = package
        if package.get("quality", {}).get("overall_score"):
            pkg.rubric_overall = package["quality"]["overall_score"]
    db.commit()
    return {"message": "已保存"}


@router.post("/{task_id}/regenerate")
def regenerate_agent(
    task_id: str,
    body: RegenerateRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = db.query(CaseTask).filter(CaseTask.id == task_id, CaseTask.user_id == user.id).first()
    if not task:
        raise HTTPException(404, "任务不存在")
    background_tasks.add_task(_run_generation_bg, task_id)
    return {"message": f"已触发 {body.agent} 重新生成", "task_id": task_id}


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
