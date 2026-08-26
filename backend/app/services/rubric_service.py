"""案例 Rubric 规则评分服务"""

from __future__ import annotations

import re
from typing import Any


def score_package(package: dict[str, Any]) -> dict[str, Any]:
    """基于规则计算五维分与总分，写入 package['quality']。"""
    body = package.get("body") or {}
    questions = package.get("discussion_questions") or []
    objectives = package.get("learning_objectives") or []
    alignment = package.get("alignment_matrix") or []
    guide = package.get("instructor_guide") or {}
    body_text = "".join(
        str(body.get(key) or "") for key in ("background", "narrative", "decision_point")
    )
    actual_words = len(re.sub(r"\s+", "", body_text))
    target_words = int((package.get("meta") or {}).get("target_words") or 0)

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
    discipline_authenticity = None
    if (package.get("meta") or {}).get("content_mode") == "discipline_contract":
        blueprint = package.get("case_blueprint") or {}
        required = blueprint.get("required_elements") or []
        artifacts = package.get("discipline_artifacts") or {}
        expected = {str(item.get("key")) for item in required if isinstance(item, dict)}
        covered = {str(item.get("key")) for item in package.get("discipline_coverage") or [] if isinstance(item, dict) and str(item.get("body_evidence") or "").strip()}
        completeness = len(expected & covered) / max(len(expected), 1)
        discipline_authenticity = round(5.0 if completeness == 1 and artifacts else 2.5 + completeness * 2, 1)
        authenticity = min(authenticity, discipline_authenticity)

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

    # 可读性：正文是否兑现用户设定的目标篇幅
    readability = 3.5
    ratio = actual_words / target_words if target_words else 0
    if target_words and 0.95 <= ratio <= 1.05:
        readability = 4.5
    elif target_words and 0.85 <= ratio <= 1.15:
        readability = 4.3
    elif target_words and 0.7 <= ratio <= 1.3:
        readability = 4.0
    elif not target_words and 800 <= actual_words <= 6000:
        readability = 4.3

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
    if target_words and actual_words < target_words * 0.95:
        issues.append(f"案例正文仅 {actual_words} 字，未达到 {target_words} 字目标")
    elif target_words and actual_words > target_words * 1.05:
        issues.append(f"案例正文 {actual_words} 字，超出 {target_words} 字目标")

    meta = package.setdefault("meta", {})
    meta["actual_words"] = actual_words
    meta["word_count_scope"] = "背景、案例叙述与决策点的可见字符（不计空白）"

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
    if discipline_authenticity is not None:
        package["quality"]["discipline_authenticity"] = discipline_authenticity
    return package["quality"]
