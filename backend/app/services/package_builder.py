"""任务参数驱动的教学案例四件套构建（Mock / LLM 后处理共用）"""

from __future__ import annotations

from typing import Any

from app.models import CaseTask
from app.services.rubric_service import score_package


def _objectives(task: CaseTask) -> list[dict[str, Any]]:
    objs = task.learning_objectives or []
    if not objs:
        objs = [f"理解并分析「{task.title}」中的关键决策"]
    return [
        {
            "id": f"LO{i + 1}",
            "level": "分析" if i == 0 else ("评价" if i == 1 else "应用"),
            "description": obj,
            "assessment_hint": "课堂讨论与汇报",
        }
        for i, obj in enumerate(objs)
    ]


def build_structured_package(task: CaseTask, *, domain_notes: str | None = None) -> dict[str, Any]:
    """根据任务参数生成完整 CasePackage（无 LLM 时的高质量结构化产出）。"""
    lo_items = _objectives(task)
    title = task.title
    subject = task.subject
    course = task.course_name
    hours = (task.config or {}).get("class_hours") or 2
    special = (task.config or {}).get("special_requirements") or ""
    domain = domain_notes or f"{subject}领域常见术语与情境约束已纳入叙事。"

    characters = [
        {"name": "陈启明", "role": "决策者/负责人", "stance": "倾向推进既定方案"},
        {"name": "林晓雯", "role": "中层协调者", "stance": "呼吁兼顾执行层反馈"},
        {"name": "赵磊", "role": "一线代表", "stance": "担忧节奏与资源不足"},
    ]

    package: dict[str, Any] = {
        "meta": {
            "title": title,
            "subject": subject,
            "course": course,
            "difficulty": task.difficulty,
            "case_type": task.case_type,
            "target_audience": task.target_audience,
            "fictional_disclaimer": "本案例为教学虚构情境，不代表任何真实企业或个人。",
        },
        "learning_objectives": lo_items,
        "body": {
            "background": (
                f"【背景】围绕「{title}」，某组织在{subject}实践中面临战略意图与一线执行的张力。"
                f"课程《{course}》面向{task.target_audience}学生，难度定位为{task.difficulty}。"
                f"{domain} "
                f"{('教师补充要求：' + special) if special else ''}"
            ).strip(),
            "narrative": (
                f"【叙事】近期，组织围绕「{title}」召开关键协调会。"
                "陈启明强调窗口期与目标承诺，要求按原计划推进；"
                "林晓雯整理了跨部门反馈，指出沟通不足与节奏过快已引发抵触；"
                "赵磊代表执行层提出资源与能力准备不足，若强行推进可能影响质量与士气。"
                "会议中信息并不对称：决策层看到的是指标与外部压力，一线看到的是流程摩擦与加班负荷。"
                "冲突在是否调整推进节奏这一问题上集中爆发，各方立场公开化。"
                f"案例类型为「{task.case_type}」，目标篇幅约 {task.target_words} 字，"
                "正文需保留足够模糊空间，供课堂多角度解读。"
            ),
            "decision_point": (
                f"在「{title}」情境下，决策者必须在会前明确："
                "（A）按原计划全面推进；（B）局部暂停并补齐沟通与培训；"
                "（C）调整目标与里程碑，换取执行层支持。请说明依据与风险。"
            ),
            "characters": characters,
        },
        "discussion_questions": [
            {
                "level": "理解",
                "question": f"案例中各方对「{title}」的核心诉求分别是什么？依据哪些事实？",
                "teaching_intent": "识别立场与信息来源",
            },
            {
                "level": "分析",
                "question": "冲突背后反映了哪些组织、管理或专业机制问题？",
                "teaching_intent": "穿透表象到结构因素",
            },
            {
                "level": "分析",
                "question": f"结合{subject}理论，如何解释林晓雯与赵磊的立场差异？",
                "teaching_intent": "理论迁移",
            },
            {
                "level": "评价",
                "question": "三种应对策略（全面推进/局部暂停/调整目标）的利弊如何评估？",
                "teaching_intent": "权衡决策标准",
            },
            {
                "level": "创造",
                "question": "若由你决策，将采取何种方案？请给出行动步骤与沟通计划。",
                "teaching_intent": "方案设计与课堂辩论",
            },
        ],
        "instructor_guide": {
            "teaching_flow": (
                f"建议 {hours} 课时：阅读案例(20min)→小组讨论决策点(25min)"
                "→班级汇报与教师点评(20min)→总结对齐教学目标(余下时间)"
            ),
            "key_points": [
                "利益相关方分析",
                "决策标准与风险权衡",
                f"{subject}相关理论视角",
            ],
            "common_misconceptions": [
                "将问题简化为单一技术或效率问题",
                "忽略一线信息与决策层信息的不对称",
            ],
            "extension_reading": [],
        },
        "alignment_matrix": [
            {
                "objective_id": lo["id"],
                "case_section": "决策点与角色立场" if i == 0 else "讨论题与汇报",
                "activity": "小组讨论" if i % 2 == 0 else "班级辩论",
                "assessment": "汇报点评",
            }
            for i, lo in enumerate(lo_items)
        ],
        "quality": {},
    }
    score_package(package)
    return package


def merge_agent_output(package: dict[str, Any], agent: str, data: dict[str, Any]) -> dict[str, Any]:
    """将单个 Agent 的 JSON 产出合并进案例包。"""
    if agent == "CasePlanner":
        if data.get("learning_objectives"):
            package["learning_objectives"] = data["learning_objectives"]
        if data.get("outline"):
            body = package.setdefault("body", {})
            body["background"] = data["outline"].get("background", body.get("background", ""))
            body["decision_point"] = data["outline"].get("decision_point", body.get("decision_point", ""))
            if data["outline"].get("characters"):
                body["characters"] = data["outline"]["characters"]
        if data.get("characters"):
            package.setdefault("body", {})["characters"] = data["characters"]
        if data.get("decision_point"):
            package.setdefault("body", {})["decision_point"] = data["decision_point"]
    elif agent == "DomainExpert":
        notes = data.get("domain_notes") or data.get("terminology") or ""
        if notes:
            bg = package.setdefault("body", {}).get("background", "")
            package["body"]["background"] = f"{bg}\n\n【学科注释】{notes}".strip()
        if data.get("characters"):
            package.setdefault("body", {})["characters"] = data["characters"]
    elif agent == "CaseWriter":
        body = package.setdefault("body", {})
        for k in ("background", "narrative", "decision_point", "characters"):
            if data.get(k):
                body[k] = data[k]
        if data.get("body"):
            body.update({k: v for k, v in data["body"].items() if v})
    elif agent == "PedagogyDesigner":
        if data.get("discussion_questions"):
            package["discussion_questions"] = data["discussion_questions"]
        if data.get("instructor_guide"):
            package["instructor_guide"] = data["instructor_guide"]
        if data.get("alignment_matrix"):
            package["alignment_matrix"] = data["alignment_matrix"]
    elif agent == "Reviewer":
        if data.get("quality"):
            package["quality"] = data["quality"]
        elif data.get("rubric_scores") or data.get("overall_score"):
            package["quality"] = {
                "rubric_scores": data.get("rubric_scores", {}),
                "reviewer_summary": data.get("reviewer_summary", ""),
                "overall_score": data.get("overall_score", 0),
            }
        else:
            score_package(package)
    return package
