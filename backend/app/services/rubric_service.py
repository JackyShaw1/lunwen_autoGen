"""案例 Rubric 规则评分服务"""

from __future__ import annotations

from typing import Any


def score_package(package: dict[str, Any]) -> dict[str, Any]:
    """基于规则计算五维分与总分，写入 package['quality']。"""
    body = package.get("body") or {}
    questions = package.get("discussion_questions") or []
    objectives = package.get("learning_objectives") or []
    alignment = package.get("alignment_matrix") or []
    guide = package.get("instructor_guide") or {}
    narrative = (body.get("narrative") or "") + (body.get("background") or "")

    # 对齐度：目标与对齐表
    alignment_score = 3.0
    if objectives and alignment:
        alignment_score = 4.5 if len(alignment) >= len(objectives) else 4.0
    elif objectives:
        alignment_score = 3.5

    # 真实性：角色 + 决策点
    authenticity = 3.0
    chars = body.get("characters") or []
    if body.get("decision_point") and len(chars) >= 2:
        authenticity = 4.3
    elif body.get("decision_point"):
        authenticity = 3.8

    # 讨论价值：讨论题数量与分层
    discussion = 3.0
    levels = {q.get("level") for q in questions if q.get("level")}
    if len(questions) >= 5 and len(levels) >= 3:
        discussion = 4.5
    elif len(questions) >= 4:
        discussion = 4.1
    elif len(questions) >= 2:
        discussion = 3.5

    # 结构：背景/叙事/决策点齐全
    structure = 3.0
    parts = sum(1 for k in ("background", "narrative", "decision_point") if body.get(k))
    structure = {0: 2.5, 1: 3.2, 2: 3.8, 3: 4.4}.get(parts, 3.0)

    # 可读性：篇幅
    readability = 3.5
    n = len(narrative)
    if 800 <= n <= 6000:
        readability = 4.3
    elif n > 400:
        readability = 4.0

    if guide.get("teaching_flow") and guide.get("key_points"):
        structure = min(5.0, structure + 0.2)

    scores = {
        "alignment": round(alignment_score, 1),
        "authenticity": round(authenticity, 1),
        "discussion": round(discussion, 1),
        "structure": round(structure, 1),
        "readability": round(readability, 1),
    }
    overall = round(sum(scores.values()) / len(scores), 1)

    issues = []
    if not body.get("decision_point"):
        issues.append("缺少决策点")
    if len(questions) < 4:
        issues.append("讨论题少于 4 题")
    if not alignment:
        issues.append("目标对齐表为空")

    summary = (
        f"Rubric 综合 {overall}。"
        + (" 建议修订：" + "；".join(issues) if issues else " 决策点与讨论结构完整，可用于课堂。")
    )

    package["quality"] = {
        "rubric_scores": scores,
        "reviewer_summary": summary,
        "overall_score": overall,
        "issues": issues,
    }
    return package["quality"]
