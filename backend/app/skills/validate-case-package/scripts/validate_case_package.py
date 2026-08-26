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

    meta = package.get("meta") or {}
    if meta.get("content_mode") == "discipline_contract":
        blueprint = package.get("case_blueprint") or {}
        if not blueprint.get("approved"):
            issues.append(_issue("error", "blueprint_not_approved", "案例蓝图未经教师确认", "case_blueprint.approved"))
        contract_id = str(meta.get("course_contract_id") or blueprint.get("contract_id") or "")
        artifacts = package.get("discipline_artifacts") or {}
        normalized_body = re.sub(r"\s+", "", visible_body)
        expected_keys = {str(item.get("key")) for item in blueprint.get("required_elements") or [] if isinstance(item, dict)}
        coverage = package.get("discipline_coverage") or []
        valid_coverage: set[str] = set()
        for item in coverage:
            if not isinstance(item, dict):
                continue
            evidence = str(item.get("body_evidence") or "").strip()
            if len(evidence) >= 4 and evidence in visible_body:
                valid_coverage.add(str(item.get("key") or ""))
        missing_coverage = expected_keys - valid_coverage
        if missing_coverage:
            issues.append(_issue(
                "error", "discipline_coverage_missing",
                "正文没有提供可核验的学科契约覆盖证据：" + "、".join(sorted(missing_coverage)),
                "discipline_coverage",
            ))
        if not isinstance(artifacts, dict) or not artifacts:
            issues.append(_issue(
                "error", "discipline_artifacts_empty",
                "案例缺少可检查的专业产物；应提供数据、公式、条款、代码、时间线、试验或本课程对应证据",
                "discipline_artifacts",
            ))
        contract_checks = {
            "stochastic_programming": {
                "terms": ["随机变量", "情景", "概率", "决策变量", "目标函数", "约束", "追索"],
                "artifacts": ["scenario_table", "variables", "objective_function", "constraints"],
            },
            "contract_law": {
                "terms": ["合同条款", "验收", "解除", "违约", "抗辩", "证据", "救济"],
                "artifacts": ["jurisdiction", "clauses", "chronology", "legal_issues"],
            },
        }.get(contract_id)
        if contract_checks:
            missing_terms = [term for term in contract_checks["terms"] if term not in normalized_body]
            if missing_terms:
                issues.append(_issue("error", "discipline_elements_missing", "正文缺少课程必备要素：" + "、".join(missing_terms), "body"))
            missing_artifacts = [key for key in contract_checks["artifacts"] if not artifacts.get(key)]
            if missing_artifacts:
                issues.append(_issue("error", "discipline_artifacts_missing", "案例缺少专业数据或证据结构：" + "、".join(missing_artifacts), "discipline_artifacts"))
        forbidden = [str(item) for item in blueprint.get("forbidden_patterns") or [] if str(item)]
        used_forbidden = [item for item in forbidden if item in visible_body]
        if used_forbidden:
            issues.append(_issue("error", "generic_template_leak", "正文混入被课程契约禁止的通用套壳内容：" + "、".join(used_forbidden), "body"))
        generic_names = {"陈启明", "林晓雯", "赵磊"}
        used_names = {str(item.get("name") or "") for item in body.get("characters") or [] if isinstance(item, dict)}
        if generic_names & used_names:
            issues.append(_issue("error", "generic_template_characters", "课程案例仍在使用通用组织变革模板人物", "body.characters"))

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
        if meta.get("content_mode") != "source_grounded":
            issues.append(_issue("error", "grounding_mode_missing", "教师要求事实准确，案例必须使用来源约束模式", "meta.content_mode"))
        if "教学虚构" in str(meta.get("fictional_disclaimer") or ""):
            issues.append(_issue("error", "fictional_content_forbidden", "教师禁止虚构，但案例仍标记为教学虚构", "meta.fictional_disclaimer"))
        sources = package.get("evidence_sources") or []
        if len(sources) < 5:
            issues.append(_issue("error", "insufficient_evidence_sources", "事实案例至少需要5个可追溯权威来源，并以约10项为目标", "evidence_sources"))
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
    if len(visual_assets) > 10:
        issues.append(_issue("error", "too_many_visual_assets", "官方视觉素材最多选择 10 张", "visual_assets"))
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

    videos = package.get("video_resources") or []
    if len(videos) > 10:
        issues.append(_issue("error", "too_many_video_resources", "视频资源最多推荐 10 项", "video_resources"))
    video_ids: set[str] = set()
    for index, video in enumerate(videos):
        path = f"video_resources.{index}"
        if not isinstance(video, dict):
            issues.append(_issue("error", "invalid_video_resource", "视频资源结构无效", path))
            continue
        video_id = str(video.get("id") or "").strip()
        if not video_id or video_id in video_ids:
            issues.append(_issue("error", "duplicate_video_resource", "视频资源 ID 缺失或重复", path))
        video_ids.add(video_id)
        required = ("title", "source_org", "source_page_url", "video_url", "usage", "trust_level")
        if not all(str(video.get(key) or "").strip() for key in required):
            issues.append(_issue("error", "incomplete_video_provenance", "视频缺少标题、机构、来源页、播放地址、用途或可信等级", path))
        if not str(video.get("source_page_url") or "").startswith("https://") or not str(video.get("video_url") or "").startswith("https://"):
            issues.append(_issue("error", "unsafe_video_source", "视频来源页和播放地址必须使用 HTTPS", path))
        if str(video.get("trust_level") or "") not in {"official", "trusted"}:
            issues.append(_issue("error", "untrusted_video_source", "视频必须来自官方或已审核高可信来源", path))

    targets = package.get("resource_targets") or {}
    for key, actual, label in (
        ("evidence_sources", len(package.get("evidence_sources") or []), "案例事实来源"),
        ("official_visuals", len(visual_assets), "官方视觉素材"),
        ("videos", len(videos), "视频资源"),
    ):
        target = int(targets.get(key) or 0)
        if target and actual < max(target - 2, 1):
            issues.append(_issue(
                "warning", "resource_target_shortfall",
                f"{label}当前 {actual} 项，目标约 {target} 项；应继续补充可信来源，但不得用无关内容凑数",
                key,
            ))

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
