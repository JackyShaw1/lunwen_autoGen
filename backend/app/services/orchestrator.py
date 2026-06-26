"""Mock 教学案例生成流水线 — 无 LLM API 时模拟 AutoGen 五 Agent 协作"""

import asyncio
import random
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.config import settings
from app.models import AgentRunLog, CasePackage, CaseTask
from app.services.progress_hub import progress_hub


AGENT_SEQUENCE = [
    ("CasePlanner", "案例结构策划", "输出案例大纲：背景-冲突-决策点结构"),
    ("DomainExpert", "学科情境", "补充行业背景与专业术语约束"),
    ("CaseWriter", "案例撰写", "撰写案例正文叙事"),
    ("PedagogyDesigner", "讨论题设计", "生成分层讨论题与教师引导要点"),
    ("Reviewer", "质量评审", "Rubric 五维评分与通过判定"),
]


def _build_package(task: CaseTask) -> dict[str, Any]:
    objectives = task.learning_objectives or []
    lo_items = [
        {
            "id": f"LO{i+1}",
            "level": "分析",
            "description": obj,
            "assessment_hint": "课堂讨论",
        }
        for i, obj in enumerate(objectives)
    ]
    title = task.title
    return {
        "meta": {
            "title": title,
            "subject": task.subject,
            "course": task.course_name,
            "difficulty": task.difficulty,
            "case_type": task.case_type,
            "fictional_disclaimer": "本案例为教学虚构情境，不代表任何真实企业或个人",
        },
        "learning_objectives": lo_items,
        "body": {
            "background": f"{title} 的背景：某组织面临战略与执行层面的张力，多方利益相关者立场分化。",
            "narrative": (
                f"在 {task.course_name} 教学情境下，{title} 逐步展开。"
                "管理层与执行层对新举措产生分歧，冲突在关键会议前达到顶点。"
                "各方基于不同信息与利益考量，形成了难以调和的立场。"
            ),
            "decision_point": "管理层需决定是否调整推进节奏：全面继续、局部暂停或改换沟通策略。",
            "characters": [
                {"name": "张总", "role": "决策者", "stance": "坚持战略方向"},
                {"name": "李经理", "role": "中层管理者", "stance": "呼吁放缓节奏"},
                {"name": "一线代表", "role": "执行层", "stance": "担忧负担与可行性"},
            ],
        },
        "discussion_questions": [
            {"level": "理解", "question": "案例中各方核心诉求分别是什么？", "teaching_intent": "识别立场"},
            {"level": "分析", "question": "冲突背后反映了哪些组织或管理问题？"},
            {"level": "评价", "question": "不同应对策略的利弊如何评估？"},
            {"level": "创造", "question": "若由你决策，将采取何种方案并说明理由？"},
        ],
        "instructor_guide": {
            "teaching_flow": "阅读案例(20min)→小组讨论(25min)→班级汇报(15min)",
            "key_points": ["利益相关方分析", "决策点讨论", "变革管理视角"],
            "common_misconceptions": ["仅从技术或效率角度理解问题"],
            "extension_reading": [],
        },
        "alignment_matrix": [
            {
                "objective_id": lo_items[0]["id"] if lo_items else "LO1",
                "case_section": "决策点段落",
                "activity": "小组讨论",
                "assessment": "汇报点评",
            }
        ],
        "quality": {
            "rubric_scores": {
                "alignment": 4.2,
                "authenticity": 4.0,
                "discussion": 4.3,
                "structure": 4.1,
                "readability": 4.2,
            },
            "reviewer_summary": "案例具备清晰决策点与讨论价值，建议课堂重点引导中层立场分析。",
            "overall_score": 4.2,
        },
    }


async def run_mock_pipeline(db: Session, task_id: str) -> None:
    task = db.query(CaseTask).filter(CaseTask.id == task_id).first()
    if not task:
        return

    task.status = "running"
    task.error_message = None
    db.commit()

    agents_state: list[dict[str, Any]] = []
    total = len(AGENT_SEQUENCE)

    for idx, (name, _role, hint) in enumerate(AGENT_SEQUENCE):
        # running
        agents_state = []
        for j, (n, _, _) in enumerate(AGENT_SEQUENCE):
            if j < idx:
                agents_state.append({"name": n, "status": "completed", "duration_ms": random.randint(8000, 15000)})
            elif j == idx:
                agents_state.append({"name": n, "status": "running", "progress": 0})
            else:
                agents_state.append({"name": n, "status": "pending"})
        progress = int((idx / total) * 100)
        await progress_hub.publish(
            task_id,
            {
                "type": "agent_progress",
                "task_id": task_id,
                "overall_progress": progress,
                "current_agent": name,
                "agents": agents_state,
                "estimated_remaining_seconds": (total - idx) * 8,
            },
        )

        # simulate sub-progress for writer
        if name == "CaseWriter":
            for p in [30, 60, 90]:
                await asyncio.sleep(0.4)
                agents_state[idx] = {"name": name, "status": "running", "progress": p}
                await progress_hub.publish(
                    task_id,
                    {
                        "type": "agent_progress",
                        "task_id": task_id,
                        "overall_progress": progress + int(p / total),
                        "current_agent": name,
                        "agents": agents_state,
                    },
                )
        else:
            await asyncio.sleep(0.6)

        duration = random.randint(9000, 16000)
        log = AgentRunLog(
            task_id=task_id,
            agent_name=name,
            round=0,
            input_summary=f"任务: {task.title}",
            output_summary=hint,
            token_usage=random.randint(800, 2500),
            duration_ms=duration,
        )
        db.add(log)

    package_data = _build_package(task)
    overall = package_data["quality"]["overall_score"]

    pkg = CasePackage(
        task_id=task_id,
        version=1,
        package=package_data,
        rubric_overall=overall,
        status="finalized" if overall >= settings.reviewer_pass_threshold else "draft",
    )
    db.add(pkg)

    task.status = "finalized" if overall >= settings.reviewer_pass_threshold else "completed"
    task.updated_at = datetime.now(timezone.utc)
    db.commit()

    final_agents = [
        {"name": n, "status": "completed", "duration_ms": random.randint(9000, 16000)}
        for n, _, _ in AGENT_SEQUENCE
    ]
    await progress_hub.publish(
        task_id,
        {
            "type": "agent_progress",
            "task_id": task_id,
            "overall_progress": 100,
            "current_agent": "Reviewer",
            "agents": final_agents,
            "estimated_remaining_seconds": 0,
        },
    )


async def run_generation(db: Session, task_id: str) -> None:
    """统一入口：当前默认 Mock；配置 OPENAI_API_KEY + USE_MOCK_GENERATION=false 可扩展真实 LLM"""
    if settings.use_mock_generation or not settings.openai_api_key:
        await run_mock_pipeline(db, task_id)
    else:
        # 预留真实 AutoGen 流水线
        await run_mock_pipeline(db, task_id)
