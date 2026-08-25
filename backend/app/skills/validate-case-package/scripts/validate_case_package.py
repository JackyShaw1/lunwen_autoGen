"""Deterministic release checks for a teaching CasePackage."""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any


def _issue(severity: str, code: str, message: str, path: str) -> dict[str, str]:
    return {"severity": severity, "code": code, "message": message, "path": path}


def count_visible_body_chars(package: dict[str, Any]) -> int:
    body = package.get("body") or {}
    text = "".join(str(body.get(key) or "") for key in ("background", "narrative", "decision_point"))
    return len(re.sub(r"\s+", "", text))


def _repeated_paragraphs(text: str) -> bool:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n+", text or "") if len(part.strip()) >= 80]
    for index, left in enumerate(paragraphs):
        for right in paragraphs[index + 1 :]:
            if SequenceMatcher(None, left, right).ratio() >= 0.88:
                return True
    return False


def validate_case_package(package: dict[str, Any], task_context: dict[str, Any]) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    body = package.get("body") or {}
    for key in ("background", "narrative", "decision_point"):
        if not str(body.get(key) or "").strip():
            issues.append(_issue("error", "missing_body_part", f"正文缺少 {key}", f"body.{key}"))

    target = int(task_context.get("target_words") or (package.get("meta") or {}).get("target_words") or 0)
    actual = count_visible_body_chars(package)
    if target and not target * 0.95 <= actual <= target * 1.05:
        issues.append(_issue("error", "body_length", f"正文实际 {actual} 字，要求 {int(target * .95)}–{int(target * 1.05)} 字", "body"))

    characters = body.get("characters") or []
    if len(characters) < 2:
        issues.append(_issue("error", "insufficient_characters", "案例至少需要两个具有不同立场的角色", "body.characters"))
    if len(str(body.get("decision_point") or "")) < 30:
        issues.append(_issue("warning", "weak_decision_point", "决策点过短，可能缺少行动、取舍或责任主体", "body.decision_point"))
    narrative = str(body.get("narrative") or "")
    visible_body = "\n".join(str(body.get(key) or "") for key in ("background", "narrative", "decision_point"))
    if "【学科注释】" in visible_body:
        issues.append(_issue("error", "internal_note_exposed", "学科内部注释不得出现在学生可见正文中", "body"))
    if _repeated_paragraphs(narrative):
        issues.append(_issue("warning", "repeated_paragraph", "正文存在高度相似的长段落", "body.narrative"))
    if any(phrase in narrative for phrase in ("目标字数", "目标篇幅", "案例类型为")):
        issues.append(_issue("warning", "instructional_meta", "学生正文中出现生成或配置元语言", "body.narrative"))

    requirement_text = " ".join(
        str(value)
        for value in [
            *(task_context.get("learning_objectives") or []),
            (task_context.get("config") or {}).get("special_requirements", ""),
        ]
    )
    strict_grounding = any(
        term in requirement_text
        for term in (
            "不能虚假", "不得虚构", "禁止虚构", "不允许虚构", "切忌编造", "不要编造", "禁止编造",
            "数据准确", "真实案例", "事实准确",
        )
    )
    if strict_grounding:
        meta = package.get("meta") or {}
        if meta.get("content_mode") != "source_grounded":
            issues.append(_issue("error", "grounding_mode_missing", "教师要求事实准确，案例必须使用来源约束模式", "meta.content_mode"))
        if "教学虚构" in str(meta.get("fictional_disclaimer") or ""):
            issues.append(_issue("error", "fictional_content_forbidden", "教师禁止虚构，但案例仍标记为教学虚构", "meta.fictional_disclaimer"))
        sources = package.get("evidence_sources") or []
        if len(sources) < 2:
            issues.append(_issue("error", "insufficient_evidence_sources", "事实案例至少需要两个可追溯权威来源", "evidence_sources"))
        source_ids: set[str] = set()
        for index, source in enumerate(sources):
            source_id = str(source.get("id") or "") if isinstance(source, dict) else ""
            if not source_id or source_id in source_ids:
                issues.append(_issue("error", "invalid_evidence_source", "事实来源ID缺失或重复", f"evidence_sources.{index}"))
            source_ids.add(source_id)
            if not isinstance(source, dict) or not all(str(source.get(key) or "").strip() for key in ("title", "source_org", "source_page_url", "usage")):
                issues.append(_issue("error", "incomplete_evidence_source", "事实来源缺少标题、机构、链接或用途", f"evidence_sources.{index}"))
            elif not str(source.get("source_page_url") or "").startswith("https://"):
                issues.append(_issue("error", "unsafe_evidence_source", "事实来源必须使用HTTPS地址", f"evidence_sources.{index}.source_page_url"))
            elif f"[{source_id}]" not in visible_body:
                issues.append(_issue("error", "uncited_evidence_source", f"来源 {source_id} 未在正文中引用", "body"))
        teacher_requirements = package.get("teacher_requirements") or {}
        original = teacher_requirements.get("original") or []
        if len(original) != len(task_context.get("learning_objectives") or []):
            issues.append(_issue("error", "teacher_requirement_loss", "教师原始要求在Agent传递中丢失", "teacher_requirements.original"))
        anchors = teacher_requirements.get("knowledge_anchors") or []
        missing_anchors = [anchor for anchor in anchors if re.sub(r"\s+", "", str(anchor)) not in re.sub(r"\s+", "", visible_body)]
        if missing_anchors:
            issues.append(_issue("error", "knowledge_anchor_missing", "正文未覆盖教师指定知识点：" + "、".join(missing_anchors), "body"))
        if teacher_requirements.get("ideology_required"):
            ideology = package.get("course_ideology") or {}
            if not ideology.get("figure") or not ideology.get("themes") or not ideology.get("implementation"):
                issues.append(_issue("error", "course_ideology_missing", "教师要求课程思政，但人物、主题或融入方式不完整", "course_ideology"))
        fictional_names = {"陈启明", "林晓雯", "赵磊"}
        used_names = {str(item.get("name") or "") for item in body.get("characters") or [] if isinstance(item, dict)}
        if fictional_names & used_names:
            issues.append(_issue("error", "generic_fictional_characters", "事实案例混入通用虚构人物", "body.characters"))

    questions = package.get("discussion_questions") or []
    if len(questions) < 5:
        issues.append(_issue("error", "insufficient_questions", "讨论题至少需要 5 道", "discussion_questions"))
    levels = {str(item.get("level") or "") for item in questions if isinstance(item, dict)} - {""}
    if len(levels) < 3:
        issues.append(_issue("error", "insufficient_levels", "讨论题至少需要覆盖 3 个认知层级", "discussion_questions"))

    objectives = package.get("learning_objectives") or []
    if not objectives:
        issues.append(_issue("error", "missing_objectives", "案例包至少需要 1 条教学目标", "learning_objectives"))
    objective_ids = [str(item.get("id") or f"LO{index}") for index, item in enumerate(objectives, 1)]
    matrix = package.get("alignment_matrix") or []
    present_ids = {str(row.get("objective_id") or "") for row in matrix if isinstance(row, dict)}
    for objective_id in objective_ids:
        if objective_id not in present_ids:
            issues.append(_issue("error", "missing_alignment", f"{objective_id} 未出现在目标对齐表", "alignment_matrix"))
    for index, row in enumerate(matrix):
        if not isinstance(row, dict) or not all(str(row.get(key) or "").strip() for key in ("objective_id", "case_section", "activity", "assessment")):
            issues.append(_issue("error", "incomplete_alignment", f"目标对齐表第 {index + 1} 行字段不完整", f"alignment_matrix.{index}"))

    guide = package.get("instructor_guide") or {}
    for key, label in (
        ("teaching_flow", "授课流程"),
        ("key_points", "教学要点"),
        ("common_misconceptions", "常见误区"),
    ):
        if not guide.get(key):
            issues.append(_issue("error", "incomplete_instructor_guide", f"教师指南缺少{label}", f"instructor_guide.{key}"))
    flow = str(guide.get("teaching_flow") or "")
    minutes = sum(int(value) for value in re.findall(r"(\d+)\s*(?:min|分钟)", flow, flags=re.I))
    class_hours = int((task_context.get("config") or {}).get("class_hours") or task_context.get("class_hours") or 0)
    if class_hours and minutes and minutes > class_hours * 45:
        issues.append(_issue("error", "timing_overflow", f"授课环节共 {minutes} 分钟，超过 {class_hours} 课时可用的 {class_hours * 45} 分钟", "instructor_guide.teaching_flow"))
    elif class_hours and not minutes:
        issues.append(_issue("warning", "timing_missing", "授课流程没有明确分钟数", "instructor_guide.teaching_flow"))

    visual_assets = package.get("visual_assets") or []
    material_research = package.get("material_research") or {}
    if visual_assets and not str(material_research.get("context_signature") or "").strip():
        issues.append(_issue(
            "error", "missing_material_context",
            "官方视觉素材缺少课程上下文研究标记，无法确认是否属于当前课程",
            "material_research.context_signature",
        ))
    if len(visual_assets) > 6:
        issues.append(_issue("error", "too_many_visual_assets", "官方视觉素材最多选择 6 张", "visual_assets"))
    asset_ids: set[str] = set()
    for index, asset in enumerate(visual_assets):
        path = f"visual_assets.{index}"
        if not isinstance(asset, dict):
            issues.append(_issue("error", "invalid_visual_asset", "视觉素材结构无效", path))
            continue
        asset_id = str(asset.get("id") or "").strip()
        if not asset_id or asset_id in asset_ids:
            issues.append(_issue("error", "duplicate_visual_asset", "视觉素材 ID 缺失或重复", path))
        asset_ids.add(asset_id)
        required = ("title", "caption", "source_org", "source_page_url", "rights_notice")
        if not all(str(asset.get(key) or "").strip() for key in required):
            issues.append(_issue("error", "incomplete_visual_provenance", "视觉素材缺少标题、说明、来源机构、原始页面或权利提示", path))
        if not str(asset.get("source_page_url") or "").startswith("https://"):
            issues.append(_issue("error", "unsafe_visual_source", "视觉素材原始页面必须使用 HTTPS 官方地址", f"{path}.source_page_url"))
        if asset.get("official") is not True:
            issues.append(_issue("error", "unverified_visual_source", "视觉素材尚未标记为审核过的官方来源", path))

    quality = package.get("quality") or {}
    scores = quality.get("rubric_scores") or {}
    score_keys = ("alignment", "authenticity", "discussion", "structure", "readability")
    missing_score_keys = [key for key in score_keys if key not in scores]
    if missing_score_keys or quality.get("overall_score") is None:
        issues.append(_issue("error", "missing_quality_scores", "质量评审缺少完整五维评分或综合分", "quality"))
    else:
        try:
            values = [float(scores[key]) for key in score_keys]
            overall = float(quality.get("overall_score"))
            if any(not 1 <= value <= 5 for value in values) or not 1 <= overall <= 5:
                issues.append(_issue("error", "score_range", "Rubric 评分必须处于 1–5", "quality"))
            elif abs(overall - round(sum(values) / 5, 1)) > 0.11:
                issues.append(_issue("error", "score_mean", "综合分不是五项评分的算术平均值", "quality.overall_score"))
        except (TypeError, ValueError):
            issues.append(_issue("error", "score_type", "Rubric 评分必须为数字", "quality"))

    return {
        "passed": not any(issue["severity"] == "error" for issue in issues),
        "actual_body_chars": actual,
        "target_body_chars": target,
        "issues": issues,
    }
