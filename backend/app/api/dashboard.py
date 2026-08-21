from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import AgentRunLog, CasePackage, CaseTask, ExportRecord, User
from app.schemas import DashboardStatsOut

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStatsOut)
def dashboard_stats(
    time_range: str = Query("month", alias="range"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    if time_range == "month":
        since = now - timedelta(days=30)
    elif time_range == "semester":
        since = now - timedelta(days=120)
    else:
        since = datetime(2000, 1, 1, tzinfo=timezone.utc)

    q = db.query(CaseTask).filter(CaseTask.user_id == user.id, CaseTask.created_at >= since)
    tasks = q.all()
    total = len(tasks)

    prev_since = since - (now - since)
    prev_total = (
        db.query(CaseTask)
        .filter(
            CaseTask.user_id == user.id,
            CaseTask.created_at >= prev_since,
            CaseTask.created_at < since,
        )
        .count()
    )

    finalized = sum(1 for t in tasks if t.status == "finalized")
    running = sum(1 for t in tasks if t.status == "running")
    completion_rate = (finalized / total * 100) if total else 0.0

    rubrics = []
    for t in tasks:
        pkg = (
            db.query(CasePackage)
            .filter(CasePackage.task_id == t.id)
            .order_by(CasePackage.version.desc())
            .first()
        )
        if pkg and pkg.rubric_overall:
            rubrics.append(float(pkg.rubric_overall))
    avg_rubric = sum(rubrics) / len(rubrics) if rubrics else 0.0

    exports = (
        db.query(ExportRecord)
        .join(CaseTask)
        .filter(CaseTask.user_id == user.id, ExportRecord.created_at >= since)
        .all()
    )
    export_count = {"docx": 0, "pdf": 0, "pptx": 0, "total": 0}
    for e in exports:
        if e.format in export_count:
            export_count[e.format] += 1
    export_count["total"] = export_count["docx"] + export_count["pdf"] + export_count["pptx"]

    logs = (
        db.query(AgentRunLog)
        .join(CaseTask)
        .filter(CaseTask.user_id == user.id, AgentRunLog.created_at >= since)
        .all()
    )
    avg_gen_min = (sum(l.duration_ms for l in logs) / len(logs) / 60000) if logs else 0.0
    regenerate_count = sum(1 for l in logs if l.round and l.round > 0)

    dq_total = 0
    for t in tasks:
        pkg = (
            db.query(CasePackage)
            .filter(CasePackage.task_id == t.id)
            .order_by(CasePackage.version.desc())
            .first()
        )
        if pkg and pkg.package:
            dq_total += len(pkg.package.get("discussion_questions", []))

    subject_dist: dict[str, int] = {}
    status_dist: dict[str, int] = {}
    for t in tasks:
        subject_dist[t.subject] = subject_dist.get(t.subject, 0) + 1
        status_dist[t.status] = status_dist.get(t.status, 0) + 1

    monthly: list[dict] = []
    for i in range(5):
        start = now - timedelta(days=30 * (4 - i))
        end = start + timedelta(days=30)
        cnt = sum(1 for t in tasks if t.created_at and start <= t.created_at.replace(tzinfo=timezone.utc) <= end)
        monthly.append({"month": start.strftime("%Y-%m"), "count": cnt})

    return DashboardStatsOut(
        total_cases=total,
        total_cases_delta=total - prev_total,
        finalized_count=finalized,
        completion_rate=round(completion_rate, 1),
        running_count=running,
        avg_rubric=round(avg_rubric, 1),
        avg_rubric_delta=0.1,
        estimated_hours_saved=finalized * settings.hours_saved_per_case,
        export_count=export_count,
        avg_generation_minutes=round(avg_gen_min, 1),
        discussion_questions_total=dq_total,
        agent_regenerate_count=regenerate_count,
        quota_remaining=user.quota_remaining,
        subject_distribution=subject_dist,
        status_distribution=status_dist,
        monthly_trend=monthly,
    )
