"""YAML 驱动的教学案例 Sequential 生成流水线（LLM 或结构化 Mock）"""

from __future__ import annotations

import asyncio
import math
import time
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

import yaml
from sqlalchemy.orm import Session

from app.config import settings
from app.models import AgentConfig, AgentRunLog, CasePackage, CaseTask, User
from app.services.llm_client import chat_completion, extract_json, llm_available
from app.services.runtime_model_service import get_active_model_config
from app.services.package_builder import (
    build_structured_package,
    count_case_body_chars,
    ensure_mock_body_length,
    fit_teaching_flow_to_class_hours,
    merge_agent_output,
    normalize_case_package,
    update_body_length_meta,
)
from app.services.progress_hub import progress_hub
from app.services.rubric_service import score_package
from app.services.skill_loader import build_agent_skill_context, validate_package_with_skill
from app.services.course_blueprint_service import text_similarity
from app.services.auto_research_service import build_auto_research_pack
from app.services.grounded_case_service import find_grounded_profile, generation_preflight_error

import logging

logger = logging.getLogger(__name__)


AGENT_SEQUENCE = [
    "CasePlanner",
    "DomainExpert",
    "CaseWriter",
    "PedagogyDesigner",
    "Reviewer",
]

AGENT_HINTS = {
    "CasePlanner": "输出案例大纲：背景-冲突-决策点结构",
    "DomainExpert": "补充行业背景与专业术语约束",
    "CaseWriter": "撰写案例正文叙事",
    "PedagogyDesigner": "生成分层讨论题与教师引导要点",
    "Reviewer": "Rubric 五维评分与通过判定",
}


def _load_agent_config(db: Session, agent_name: str) -> dict[str, Any]:
    row = (
        db.query(AgentConfig)
        .filter(AgentConfig.agent_name == agent_name, AgentConfig.is_active == True)  # noqa: E712
        .order_by(AgentConfig.created_at.desc())
        .first()
    )
    if row:
        try:
            return yaml.safe_load(row.config_yaml) or {}
        except yaml.YAMLError:
            return {"agent_name": agent_name, "system_prompt": row.config_yaml}
    return {"agent_name": agent_name, "system_prompt": AGENT_HINTS.get(agent_name, "")}


def _task_context(task: CaseTask) -> dict[str, Any]:
    return {
        "title": task.title,
        "subject": task.subject,
        "course_name": task.course_name,
        "case_type": task.case_type,
        "difficulty": task.difficulty,
        "target_audience": task.target_audience,
        "target_words": task.target_words,
        "learning_objectives": task.learning_objectives,
        "workflow_template": task.workflow_template,
        "config": task.config or {},
    }


def _agent_user_prompt(agent: str, task: CaseTask, package: dict[str, Any]) -> str:
    ctx = _task_context(task)
    base = (
        f"教师任务参数：\n{yaml.safe_dump(ctx, allow_unicode=True)}\n"
        f"当前案例包草稿（JSON）：\n{yaml.safe_dump(package, allow_unicode=True)}\n"
        "全局资源规范：案例事实来源、官方视觉素材、推荐视觉素材和视频资源均以约10项为目标；"
        "只使用与当前课程强相关的政府、科研院所、权威出版物、权威媒体或已审核机构来源。"
        "数量不足时保留缺口，禁止编造链接、播放量或用无关资源凑数。\n"
        "目标解释规范：config.objective_brief 是教师对学生卡点、期望表现、必用方法和评价证据的原始意图；"
        "必须贯穿案例、讨论题和评价设计。若教师已编辑 learning_objectives，以编辑后的目标为最高优先级，不得静默替换。\n"
    )
    if (package.get("meta") or {}).get("content_mode") == "research_grounded":
        base += (
            "自动研究规范：先从 research_brief.sources 中选择被多条来源共同支持的单一真实企业、项目或事件作为案例主线；"
            "不得混合多个无关企业拼成一个案例。来源片段未明确提供的人名、数字、内部会议、对白和因果关系不得补写；"
            "事实必须紧邻标注来源编号，教学推断必须明确标注为分析或课堂任务。\n"
        )
    specs = {
        "CasePlanner": (
            "请输出 JSON，字段：outline{background,decision_point,characters[]}，"
            "learning_objectives[{id,level,description}]。保留教师目标原意并使用 LO1、LO2…编号；"
            "人物至少 3 个，决策点必须是学生需要完成的具体任务。"
        ),
        "DomainExpert": (
            "请输出 JSON，字段：domain_notes(string)，discipline_checklist[{key,label,acceptance}]，characters(可选更新)。"
            "domain_notes 必须包含专业机制、可用证据、关键约束和需避免的失真；"
            "如存在教师确认蓝图，discipline_checklist 必须逐项覆盖 required_elements；不要写完整正文。"
        ),
        "CaseWriter": (
            "请输出 JSON，字段：background, narrative, decision_point, characters[]，"
            "discipline_coverage[{key,label,body_evidence}]，discipline_artifacts(object)。"
            f"硬性要求：background、narrative、decision_point 三个字段合计的可见字符数（不计空白）"
            f"目标为 {task.target_words} 字，验收范围为 "
            f"{math.ceil(task.target_words * 0.95)}–{math.floor(task.target_words * 1.05)} 字。"
            "建议背景占 10%–15%、主体叙事占 75%–80%、决策点占 8%–12%。"
            "必须通过具体场景、行动、数据、对话和利益冲突充实内容，不得用提纲、重复段落或说明字数凑篇幅；"
            "如任务含 approved_blueprint，discipline_coverage 必须逐项覆盖 required_elements；body_evidence 必须是正文中真实出现的短证据片段，"
            "discipline_artifacts 必须保存本课程可检查的数据表、公式、条款、代码、时间线、试验或其他专业对象。"
            "正文中不要出现目标字数。只返回合法 JSON。"
            "若 meta.content_mode 为 research_grounded，只能依据 research_brief 中的来源片段写事实；"
            "每个关键事实必须紧邻标注[S1]、[S2]等来源编号，不得使用模型记忆补充企业名称、人物、数据或事件。"
        ),
        "PedagogyDesigner": (
            "请输出 JSON，字段：discussion_questions[{level,question,teaching_intent}]（至少5题），"
            "instructor_guide{teaching_flow,key_points[],common_misconceptions[]}，"
            "alignment_matrix[{objective_id,case_section,activity,assessment}]。"
            "讨论题至少覆盖 3 个认知层级，每个教学目标必须出现在对齐表中；"
            f"授课流程各环节必须明确分钟数，总时长不得超过 "
            f"{int((task.config or {}).get('class_hours') or 2) * 45} 分钟。"
        ),
        "Reviewer": (
            "请输出 JSON，字段：rubric_scores{alignment,authenticity,discussion,structure,readability}，"
            "overall_score(1-5)，reviewer_summary，issues[]。overall_score 必须是五项评分的算术平均值并保留1位小数。"
        ),
    }
    return base + specs.get(agent, "请输出与教学案例相关的 JSON。")


def _validate_agent_output(agent: str, data: Any, task: CaseTask) -> list[str]:
    """验证 Agent 间的交接契约，避免无效 JSON 静默流入下游。"""
    if not isinstance(data, dict) or not data:
        return ["输出必须是非空 JSON 对象"]
    if "raw" in data:
        return ["输出不是可解析的 JSON"]

    errors: list[str] = []
    if agent == "CasePlanner":
        outline = data.get("outline")
        objectives = data.get("learning_objectives")
        if not isinstance(outline, dict):
            errors.append("缺少 outline 对象")
        else:
            for key in ("background", "decision_point"):
                if not isinstance(outline.get(key), str) or not outline[key].strip():
                    errors.append(f"outline.{key} 必须为非空字符串")
            if not isinstance(outline.get("characters"), list) or len(outline["characters"]) < 3:
                errors.append("outline.characters 至少包含 3 个角色")
        if not isinstance(objectives, list) or not objectives:
            errors.append("learning_objectives 必须为非空数组")
        else:
            expected = len(task.learning_objectives or [])
            if expected and len(objectives) != expected:
                errors.append(f"learning_objectives 必须保留教师给出的 {expected} 条目标")
            for index, objective in enumerate(objectives, 1):
                if not isinstance(objective, dict) or not str(objective.get("description") or "").strip():
                    errors.append(f"第 {index} 条教学目标缺少 description")

    elif agent == "DomainExpert":
        if not isinstance(data.get("domain_notes"), str) or not data["domain_notes"].strip():
            errors.append("domain_notes 必须为非空字符串")
        blueprint = (task.config or {}).get("approved_blueprint") or {}
        if blueprint.get("required_elements"):
            checklist = data.get("discipline_checklist")
            if not isinstance(checklist, list):
                errors.append("discipline_checklist 必须为数组")
            else:
                expected = {str(item.get("key")) for item in blueprint["required_elements"] if isinstance(item, dict)}
                present = {str(item.get("key")) for item in checklist if isinstance(item, dict) and item.get("acceptance")}
                missing = expected - present
                if missing:
                    errors.append("discipline_checklist 缺少课程要素：" + "、".join(sorted(missing)))
        if "characters" in data and not isinstance(data["characters"], list):
            errors.append("characters 必须为数组")

    elif agent == "CaseWriter":
        for key in ("background", "narrative", "decision_point"):
            if not isinstance(data.get(key), str) or not data[key].strip():
                errors.append(f"{key} 必须为非空字符串")
        if not isinstance(data.get("characters"), list) or len(data["characters"]) < 2:
            errors.append("characters 至少包含 2 个角色")
        if ((task.config or {}).get("auto_research_pack") or {}).get("sources"):
            visible = " ".join(str(data.get(key) or "") for key in ("background", "narrative", "decision_point"))
            cited = set(re.findall(r"\[S\d+\]", visible))
            if len(cited) < 3:
                errors.append("真实案例正文至少引用 3 个不同的已检索来源编号（如 [S1][S2][S3]）")
        blueprint = (task.config or {}).get("approved_blueprint") or {}
        if blueprint.get("required_elements"):
            coverage = data.get("discipline_coverage")
            artifacts = data.get("discipline_artifacts")
            if not isinstance(coverage, list):
                errors.append("discipline_coverage 必须为数组")
            else:
                visible = " ".join(str(data.get(key) or "") for key in ("background", "narrative", "decision_point"))
                expected = {str(item.get("key")) for item in blueprint["required_elements"] if isinstance(item, dict)}
                covered = {
                    str(item.get("key")) for item in coverage
                    if isinstance(item, dict) and len(str(item.get("body_evidence") or "").strip()) >= 4
                    and str(item.get("body_evidence") or "").strip() in visible
                }
                missing = expected - covered
                if missing:
                    errors.append("discipline_coverage 缺少正文证据：" + "、".join(sorted(missing)))
            if not isinstance(artifacts, dict) or not artifacts:
                errors.append("discipline_artifacts 必须提供可检查的专业数据、条款、公式、代码、时间线或试验对象")

    elif agent == "PedagogyDesigner":
        questions = data.get("discussion_questions")
        if not isinstance(questions, list) or len(questions) < 5:
            errors.append("discussion_questions 至少包含 5 题")
        else:
            levels = {str(question.get("level") or "") for question in questions if isinstance(question, dict)}
            if len(levels - {""}) < 3:
                errors.append("讨论题至少覆盖 3 个认知层级")
            for index, question in enumerate(questions, 1):
                if not isinstance(question, dict) or not all(
                    str(question.get(key) or "").strip() for key in ("level", "question", "teaching_intent")
                ):
                    errors.append(f"第 {index} 道讨论题字段不完整")
        guide = data.get("instructor_guide")
        if not isinstance(guide, dict):
            errors.append("instructor_guide 必须为对象")
        else:
            if not str(guide.get("teaching_flow") or "").strip():
                errors.append("instructor_guide.teaching_flow 必须为非空字符串")
            if not isinstance(guide.get("key_points"), list) or not guide["key_points"]:
                errors.append("instructor_guide.key_points 必须为非空数组")
            if not isinstance(guide.get("common_misconceptions"), list) or not guide["common_misconceptions"]:
                errors.append("instructor_guide.common_misconceptions 必须为非空数组")
        matrix = data.get("alignment_matrix")
        expected = len(task.learning_objectives or [])
        if not isinstance(matrix, list) or len(matrix) < max(expected, 1):
            errors.append("alignment_matrix 必须覆盖全部教学目标")
        elif expected:
            present = {str(row.get("objective_id") or "") for row in matrix if isinstance(row, dict)}
            missing = [f"LO{i}" for i in range(1, expected + 1) if f"LO{i}" not in present]
            if missing:
                errors.append("alignment_matrix 缺少目标：" + "、".join(missing))
        if isinstance(matrix, list):
            for index, row in enumerate(matrix, 1):
                if not isinstance(row, dict) or not all(
                    str(row.get(key) or "").strip()
                    for key in ("objective_id", "case_section", "activity", "assessment")
                ):
                    errors.append(f"alignment_matrix 第 {index} 行字段不完整")

    elif agent == "Reviewer":
        scores = data.get("rubric_scores")
        keys = ("alignment", "authenticity", "discussion", "structure", "readability")
        if not isinstance(scores, dict):
            errors.append("rubric_scores 必须为对象")
        else:
            values: list[float] = []
            for key in keys:
                try:
                    value = float(scores.get(key))
                except (TypeError, ValueError):
                    errors.append(f"rubric_scores.{key} 必须是 1–5 的数字")
                    continue
                if not 1 <= value <= 5:
                    errors.append(f"rubric_scores.{key} 超出 1–5")
                values.append(value)
            try:
                overall = float(data.get("overall_score"))
                if not 1 <= overall <= 5:
                    errors.append("overall_score 超出 1–5")
                elif len(values) == 5 and abs(overall - round(sum(values) / 5, 1)) > 0.11:
                    errors.append("overall_score 不是五项评分的算术平均值")
            except (TypeError, ValueError):
                errors.append("overall_score 必须是 1–5 的数字")
        if not isinstance(data.get("reviewer_summary"), str) or not data["reviewer_summary"].strip():
            errors.append("reviewer_summary 必须为非空字符串")
        if not isinstance(data.get("issues"), list):
            errors.append("issues 必须为数组")
    return errors


def _canonicalize_agent_output(
    agent: str,
    data: Any,
    task: CaseTask,
    package: dict[str, Any],
) -> dict[str, Any]:
    """修复常见的兼容模型字段漂移，同时保留需要模型负责的实质内容。"""
    if not isinstance(data, dict):
        return {"raw": data}
    result = dict(data)
    if agent == "CasePlanner":
        outline = result.get("outline") if isinstance(result.get("outline"), dict) else {}
        outline = dict(outline)
        body = package.get("body") or {}
        for key in ("background", "decision_point"):
            if not str(outline.get(key) or "").strip():
                candidate = result.get(key) or body.get(key)
                if candidate:
                    outline[key] = str(candidate)

        characters = outline.get("characters") or result.get("characters") or []
        valid_characters = [item for item in characters if isinstance(item, dict)]
        seen = {
            str(item.get("name") or item.get("role") or "").strip()
            for item in valid_characters
        }
        for item in body.get("characters") or []:
            marker = str(item.get("name") or item.get("role") or "").strip() if isinstance(item, dict) else ""
            if isinstance(item, dict) and marker and marker not in seen:
                valid_characters.append(deepcopy(item))
                seen.add(marker)
            if len(valid_characters) >= 3:
                break
        outline["characters"] = valid_characters
        result["outline"] = outline

        # 教学目标是教师已确认的上游契约，不允许兼容模型改名、删减或改写。
        canonical_objectives = package.get("learning_objectives") or []
        if canonical_objectives:
            result["learning_objectives"] = deepcopy(canonical_objectives)

    elif agent == "DomainExpert":
        blueprint = (task.config or {}).get("approved_blueprint") or {}
        checklist = [
            dict(item) for item in result.get("discipline_checklist") or []
            if isinstance(item, dict)
        ]
        present = {str(item.get("key")) for item in checklist}
        for item in blueprint.get("required_elements") or []:
            key = str(item.get("key") or "") if isinstance(item, dict) else ""
            if key and key not in present:
                checklist.append({
                    "key": key,
                    "label": item.get("label"),
                    "acceptance": item.get("planned_use"),
                })
        if checklist:
            result["discipline_checklist"] = checklist

    elif agent == "Reviewer":
        scores = result.get("rubric_scores")
        keys = ("alignment", "authenticity", "discussion", "structure", "readability")
        if isinstance(scores, dict):
            try:
                values = [float(scores[key]) for key in keys]
                if all(1 <= value <= 5 for value in values):
                    result["overall_score"] = round(sum(values) / len(values), 1)
            except (KeyError, TypeError, ValueError):
                pass
    return result


async def _run_agent_llm(
    db: Session,
    agent: str,
    task: CaseTask,
    package: dict[str, Any],
    *,
    on_delta: Any = None,
) -> tuple[dict[str, Any], str, int]:
    cfg = _load_agent_config(db, agent)
    system = cfg.get("system_prompt") or AGENT_HINTS.get(agent, "")
    skill_context, _ = build_agent_skill_context(agent, cfg, _task_context(task))
    if skill_context:
        system += "\n\n# 本次任务已加载的共享 Skills\n\n" + skill_context
    model_cfg = cfg.get("model") or {}
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": _agent_user_prompt(agent, task, package)},
    ]
    max_tokens = int(model_cfg.get("max_tokens", 4096))
    if agent == "CaseWriter":
        max_tokens = max(max_tokens, min(16000, task.target_words * 2 + 2000))
    configured_model = str(model_cfg.get("name") or "").strip()
    use_model = get_active_model_config(db).model if configured_model in ("", "inherit") else configured_model
    content = await chat_completion(
        messages,
        temperature=float(model_cfg.get("temperature", 0.7)),
        max_tokens=max_tokens,
        model=use_model,
        on_delta=on_delta,
    )
    total_content = content
    try:
        data = extract_json(content)
    except Exception:
        data = {"raw": content}
    data = _canonicalize_agent_output(agent, data, task, package)
    errors = _validate_agent_output(agent, data, task)
    if errors:
        correction = (
            "上一次输出未通过结构契约校验：\n- "
            + "\n- ".join(errors)
            + "\n请依据原任务完整重做，只返回满足契约的合法 JSON，不要解释。"
        )
        repaired_content = await chat_completion(
            messages + [{"role": "assistant", "content": content}, {"role": "user", "content": correction}],
            temperature=min(float(model_cfg.get("temperature", 0.7)), 0.3),
            max_tokens=max_tokens,
            model=use_model,
            on_delta=on_delta,
        )
        total_content += repaired_content
        try:
            data = extract_json(repaired_content)
        except Exception as exc:
            raise ValueError(f"{agent} 纠错后仍未返回合法 JSON") from exc
        data = _canonicalize_agent_output(agent, data, task, package)
        errors = _validate_agent_output(agent, data, task)
        if errors:
            raise ValueError(f"{agent} 输出契约校验失败：{'；'.join(errors)}")
        content = repaired_content
    summary = content[:240].replace("\n", " ")
    tokens = max(len(total_content) // 3, 1)
    return data, summary, tokens


async def _repair_casewriter_length(
    db: Session,
    task: CaseTask,
    package: dict[str, Any],
    *,
    on_delta: Any = None,
) -> tuple[dict[str, Any], int]:
    """让 LLM 对不足篇幅的正文定向扩写；返回最终输出和额外 token 估算。"""
    minimum = math.ceil(task.target_words * 0.95)
    maximum = math.floor(task.target_words * 1.05)
    extra_tokens = 0
    for attempt in range(2):
        actual = count_case_body_chars(package)
        if minimum <= actual <= maximum:
            break
        body = package.get("body") or {}
        prompt = (
            "你是教学案例正文修订专家。当前正文未通过篇幅验收，请在保留人物、事实逻辑和决策冲突的基础上重写并调整篇幅。\n"
            f"当前可见字符数：{actual}；目标：{task.target_words}；合格范围：{minimum}–{maximum}。\n"
            "篇幅不足时重点补充具体场景、行动过程、数据证据、角色对话、利益权衡和逐步升级的冲突；篇幅超出时压缩次要信息。"
            "不得复制段落、空泛总结或在正文中谈论字数。\n"
            "保留并更新 discipline_coverage 与 discipline_artifacts，确保每个 body_evidence 仍能在修订后正文中原样找到。"
            "只返回 JSON：{background:string,narrative:string,decision_point:string,characters:array,discipline_coverage:array,discipline_artifacts:object}。\n"
            f"当前正文：\n{yaml.safe_dump(body, allow_unicode=True)}"
        )
        cfg = _load_agent_config(db, "CaseWriter")
        system = cfg.get("system_prompt") or AGENT_HINTS["CaseWriter"]
        model_cfg = cfg.get("model") or {}
        configured_model = str(model_cfg.get("name") or "").strip()
        use_model = get_active_model_config(db).model if configured_model in ("", "inherit") else configured_model
        content = await chat_completion(
            [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            temperature=0.65,
            max_tokens=min(16000, task.target_words * 2 + 2000),
            model=use_model,
            on_delta=on_delta,
        )
        extra_tokens += max(len(content) // 3, 1)
        repaired = extract_json(content)
        if not isinstance(repaired, dict):
            raise ValueError(f"第 {attempt + 1} 次篇幅修订未返回合法 JSON")
        package = merge_agent_output(package, "CaseWriter", repaired)
    return package, extra_tokens


def _run_agent_mock(agent: str, task: CaseTask, package: dict[str, Any]) -> tuple[dict[str, Any], str, int]:
    """结构化 Mock：按 Agent 职责增量完善案例包。"""
    if agent == "CasePlanner":
        data = {
            "outline": {
                "background": package["body"]["background"],
                "decision_point": package["body"]["decision_point"],
                "characters": package["body"]["characters"],
            },
            "learning_objectives": package["learning_objectives"],
        }
        summary = "已生成案例大纲与学习目标结构"
    elif agent == "DomainExpert":
        content_mode = (package.get("meta") or {}).get("content_mode")
        grounded = content_mode == "source_grounded"
        contract_driven = content_mode == "discipline_contract"
        teacher = package.get("teacher_requirements") or {}
        blueprint = package.get("case_blueprint") or {}
        data = {
            "domain_notes": (
                "事实型案例约束：知识锚点为"
                + "、".join(teacher.get("knowledge_anchors") or [])
                + "；所有事实必须对应 evidence_sources，推断需明确标注，禁止虚构人物、数据和历史对话。"
                if grounded else (
                "课程内容契约：" + "；".join(
                    f"{item.get('label')}—{item.get('planned_use')}"
                    for item in blueprint.get("required_elements") or []
                ) + "。正文必须呈现相应专业对象、证据和推理任务，禁止退化为通用组织变革故事。"
                if contract_driven else
                f"{task.subject}情境约束：术语使用需符合《{task.course_name}》教学语境，"
                "避免过度简化专业机制。"
                )
            ),
            "discipline_checklist": [
                {"key": item.get("key"), "label": item.get("label"), "acceptance": item.get("planned_use")}
                for item in blueprint.get("required_elements") or []
            ],
        }
        summary = "已补充学科情境与术语约束"
    elif agent == "CaseWriter":
        content_mode = (package.get("meta") or {}).get("content_mode")
        actual = update_body_length_meta(package, task.target_words) if content_mode in {"source_grounded", "discipline_contract"} else ensure_mock_body_length(package, task)
        data = {
            "background": package["body"]["background"],
            "narrative": package["body"]["narrative"],
            "decision_point": package["body"]["decision_point"],
            "characters": package["body"]["characters"],
            "discipline_coverage": package.get("discipline_coverage") or [],
            "discipline_artifacts": package.get("discipline_artifacts") or {},
        }
        summary = f"案例正文已通过验收：实际 {actual} 字 / 目标 {task.target_words} 字"
    elif agent == "PedagogyDesigner":
        data = {
            "discussion_questions": package["discussion_questions"],
            "instructor_guide": package["instructor_guide"],
            "alignment_matrix": package["alignment_matrix"],
        }
        summary = f"已设计 {len(package['discussion_questions'])} 道分层讨论题"
    else:
        q = score_package(package)
        data = q
        summary = f"Rubric 综合分 {q.get('overall_score')}"
    return data, summary, 1200


def _package_focus(agent: str, package: dict[str, Any], output: dict[str, Any]) -> dict[str, Any]:
    """给教师端的可读结果切片；不得携带 Agent 原始 JSON。"""
    body = package.get("body") or {}
    if agent == "CasePlanner":
        return {
            "learning_objectives": package.get("learning_objectives", []),
            "decision_point": body.get("decision_point"),
            "characters": body.get("characters", []),
        }
    if agent == "DomainExpert":
        return {
            "background": (body.get("background") or "")[:800],
            "domain_notes": output.get("domain_notes") or output.get("terminology"),
        }
    if agent == "CaseWriter":
        return {
            "background": (body.get("background") or "")[:600],
            "narrative": (body.get("narrative") or "")[:1200],
            "decision_point": body.get("decision_point"),
            "characters": body.get("characters", []),
        }
    if agent == "PedagogyDesigner":
        return {
            "discussion_questions": package.get("discussion_questions", []),
            "instructor_guide": package.get("instructor_guide", {}),
            "alignment_matrix": package.get("alignment_matrix", []),
        }
    if agent == "Reviewer":
        return {
            "quality": package.get("quality", {}),
        }
    return {}


def _agent_progress_text(agent: str) -> str:
    messages = {
        "CasePlanner": "正在梳理课程情境、教学目标、角色关系和核心决策任务…",
        "DomainExpert": "正在核对学科概念、专业机制、证据要求和事实边界…",
        "CaseWriter": "正在形成案例背景、关键事件、冲突升级和决策点…",
        "PedagogyDesigner": "正在设计课堂流程、分层讨论题和目标评价方式…",
        "Reviewer": "正在检查学科真实性、目标对齐、正文结构和教学可用性…",
    }
    return messages.get(agent, "正在形成本步骤结果…")


def focus_to_plain_text(agent: str, focus: dict[str, Any] | None) -> str:
    """与前端过程预览一致的纯文本，用于 WebSocket 流式打字推送。"""
    if not focus:
        return ""
    if agent == "CasePlanner":
        objs = focus.get("learning_objectives") or []
        chars = focus.get("characters") or []
        lines = [
            "【决策点】",
            str(focus.get("decision_point") or "—"),
            "",
            "【学习目标】",
            *[f"{i + 1}. {o.get('description', '')}" for i, o in enumerate(objs)],
            "",
            "【角色立场】",
            *[f"· {c.get('name')}（{c.get('role')}）：{c.get('stance')}" for c in chars],
        ]
        return "\n".join(lines)
    if agent == "DomainExpert":
        return "\n".join(
            [
                "【学科注释】",
                str(focus.get("domain_notes") or "—"),
                "",
                "【背景片段】",
                str(focus.get("background") or ""),
            ]
        )
    if agent == "CaseWriter":
        return "\n".join(
            [
                "【背景】",
                str(focus.get("background") or ""),
                "",
                "【叙事】",
                str(focus.get("narrative") or ""),
                "",
                "【决策点】",
                str(focus.get("decision_point") or "—"),
            ]
        )
    if agent == "PedagogyDesigner":
        qs = focus.get("discussion_questions") or []
        guide = focus.get("instructor_guide") or {}
        return "\n".join(
            [
                "【授课流程】",
                str(guide.get("teaching_flow") or "—"),
                "",
                "【讨论题】",
                *[f"{i + 1}. [{q.get('level')}] {q.get('question')}" for i, q in enumerate(qs)],
            ]
        )
    if agent == "Reviewer":
        quality = focus.get("quality") or {}
        scores = quality.get("rubric_scores") or {}
        score_lines = [f"· {k}: {v}" for k, v in scores.items()] if scores else ["—"]
        return "\n".join(
            [
                f"【综合分】 {quality.get('overall_score', '—')}",
                "",
                "【评审摘要】",
                str(quality.get("reviewer_summary") or "—"),
                "",
                "【五维评分】",
                *score_lines,
            ]
        )
    return str(focus)


async def _publish_state(
    task_id: str,
    agents_state: list[dict[str, Any]],
    overall: int,
    current: str,
    remaining: int = 0,
    *,
    step_results: list[dict[str, Any]] | None = None,
    task_meta: dict[str, Any] | None = None,
    stream: dict[str, Any] | None = None,
) -> None:
    payload: dict[str, Any] = {
        "type": "agent_progress",
        "task_id": task_id,
        "overall_progress": overall,
        "current_agent": current,
        "agents": agents_state,
        "estimated_remaining_seconds": remaining,
        "step_results": step_results or [],
        "task_meta": task_meta or {},
        "error": None,
        "failure_stage": None,
    }
    if stream is not None:
        payload["stream"] = stream
    await progress_hub.publish(task_id, payload)


async def _stream_preview_text(
    task_id: str,
    agent: str,
    full_text: str,
    agents_state: list[dict[str, Any]],
    overall: int,
    step_results: list[dict[str, Any]],
    task_meta: dict[str, Any],
) -> None:
    """按块推送过程预览文本，前端直接渲染为打字效果（与进度同步）。"""
    if not full_text:
        return
    chars = list(full_text)
    # 根据长度调节速度：短文稍慢、长文稍快，整体约 2–8 秒
    chunk = 3 if len(chars) < 400 else 6
    delay = 0.035 if len(chars) < 800 else 0.02
    buf: list[str] = []
    for i in range(0, len(chars), chunk):
        buf.extend(chars[i : i + chunk])
        await _publish_state(
            task_id,
            agents_state,
            overall,
            agent,
            step_results=step_results,
            task_meta=task_meta,
            stream={
                "agent": agent,
                "text": "".join(buf),
                "done": False,
            },
        )
        await asyncio.sleep(delay)
    await _publish_state(
        task_id,
        agents_state,
        overall,
        agent,
        step_results=step_results,
        task_meta=task_meta,
        stream={
            "agent": agent,
            "text": "".join(buf),
            "done": True,
        },
    )


def _build_agents_state(
    done_until: int,
    running: str | None,
    running_progress: int | None = None,
    *,
    step_map: dict[str, dict[str, Any]] | None = None,
) -> list[dict]:
    step_map = step_map or {}
    state = []
    for i, name in enumerate(AGENT_SEQUENCE):
        prev = step_map.get(name, {})
        if i < done_until:
            state.append(
                {
                    "name": name,
                    "status": "completed",
                    "duration_ms": prev.get("duration_ms", 10000),
                    "token_usage": prev.get("token_usage"),
                    "output_summary": prev.get("summary") or AGENT_HINTS[name],
                }
            )
        elif running and name == running:
            item: dict[str, Any] = {
                "name": name,
                "status": "running",
                "output_summary": AGENT_HINTS[name],
            }
            if running_progress is not None:
                item["progress"] = running_progress
            state.append(item)
        else:
            state.append({"name": name, "status": "pending"})
    return state


async def run_pipeline(db: Session, task_id: str) -> None:
    task = db.query(CaseTask).filter(CaseTask.id == task_id).first()
    if not task:
        return

    task.status = "running"
    task.error_message = None
    task.updated_at = datetime.now(timezone.utc)
    db.commit()

    task_meta = {
        "title": task.title,
        "subject": task.subject,
        "course_name": task.course_name,
        "case_type": task.case_type,
        "difficulty": task.difficulty,
        "target_audience": task.target_audience,
        "target_words": task.target_words,
        "learning_objectives": task.learning_objectives or [],
        "workflow_template": task.workflow_template,
        "class_hours": int((task.config or {}).get("class_hours") or 2),
    }

    try:
        preflight_error = generation_preflight_error(task)
        if preflight_error and not find_grounded_profile(task) and not (task.config or {}).get("auto_research_pack"):
            await _publish_state(
                task_id,
                _build_agents_state(0, "CasePlanner"),
                2,
                "CasePlanner",
                step_results=[],
                task_meta=task_meta,
                stream={"agent": "CasePlanner", "text": "正在自动检索真实企业案例、核验来源并建立事实资料包…", "done": False},
            )
            research_pack = await build_auto_research_pack(task)
            task.config = {**(task.config or {}), "auto_research_pack": research_pack}
            db.commit()

        latest = (
            db.query(CasePackage)
            .filter(CasePackage.task_id == task_id)
            .order_by(CasePackage.version.desc())
            .first()
        )
        package = build_structured_package(task)
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        task.status = "failed"
        task.error_message = str(exc)[:500]
        task.updated_at = datetime.now(timezone.utc)
        db.commit()
        await progress_hub.publish(task_id, {
            "type": "agent_progress", "task_id": task_id, "overall_progress": 2,
            "current_agent": None, "agents": _build_agents_state(0, None),
            "step_results": [], "task_meta": task_meta, "error": str(exc),
            "failure_stage": "agent_execution",
        })
        return
    next_version = (latest.version + 1) if latest else 1
    normalize_case_package(package)

    content_mode = (package.get("meta") or {}).get("content_mode")
    source_grounded = content_mode == "source_grounded"
    contract_driven = content_mode == "discipline_contract"
    # Audited profiles must remain deterministic: a free-form model rewrite could add
    # unsupported people, numbers or dialogue and break the teacher's evidence policy.
    use_llm = llm_available() and not source_grounded
    logger.warning(
        "generation mode task=%s use_llm=%s model=%s",
        task_id,
        use_llm,
        get_active_model_config(db).model if use_llm else "mock",
    )
    agents = list(AGENT_SEQUENCE)

    total = len(AGENT_SEQUENCE)
    step_results: list[dict[str, Any]] = []
    step_map: dict[str, dict[str, Any]] = {}
    skill_trace: dict[str, list[dict[str, Any]]] = dict(
        (package.get("meta") or {}).get("skill_trace") or {}
    )
    active_agent: str | None = None
    failure_stage = "agent_execution"
    attempt_round = db.query(AgentRunLog).filter(
        AgentRunLog.task_id == task_id,
        AgentRunLog.agent_name == AGENT_SEQUENCE[0],
    ).count()

    try:
        for step_i, agent in enumerate(agents):
            active_agent = agent
            idx = AGENT_SEQUENCE.index(agent)
            agent_cfg = _load_agent_config(db, agent)
            _, agent_skills = build_agent_skill_context(agent, agent_cfg, _task_context(task))
            skill_trace[agent] = agent_skills
            # 标记当前 Agent 运行中，右侧可先显示任务输入
            running_step = {
                "agent": agent,
                "status": "running",
                "summary": AGENT_HINTS[agent],
                "focus": None,
                "duration_ms": None,
                "token_usage": None,
            }
            # 替换同名运行中项或追加
            step_results = [s for s in step_results if s.get("agent") != agent]
            step_results.append(running_step)

            agents_state = _build_agents_state(idx, agent, 10 if agent == "CaseWriter" else None, step_map=step_map)
            # 一进入 running 就推流式占位，避免右侧长时间只显示「正在调用模型…」
            await _publish_state(
                task_id,
                agents_state,
                int(idx / total * 100),
                agent,
                (total - idx) * 6,
                step_results=step_results,
                task_meta=task_meta,
                stream={
                    "agent": agent,
                    "text": (
                        f"【{agent}】正在连接模型并生成…\n"
                        if use_llm
                        else f"【{agent}】正在生成过程预览…\n"
                    ),
                    "done": False,
                },
            )

            if agent == "CaseWriter" and not use_llm:
                for p in (30, 60, 90):
                    await asyncio.sleep(0.35)
                    agents_state = _build_agents_state(idx, agent, p, step_map=step_map)
                    await _publish_state(
                        task_id,
                        agents_state,
                        int(idx / total * 100) + int(p / total),
                        agent,
                        step_results=step_results,
                        task_meta=task_meta,
                        stream={
                            "agent": agent,
                            "text": f"【{agent}】正在生成过程预览…\n",
                            "done": False,
                        },
                    )
            else:
                await asyncio.sleep(0.15 if use_llm else 0.5)

            t0 = time.perf_counter()
            agents_state = _build_agents_state(idx, agent, 20 if agent == "CaseWriter" else None, step_map=step_map)
            overall_base = int(idx / total * 100)
            current_agent = agent  # 闭包固定本轮 agent，避免循环变量歧义

            # 节流：避免每个 token 都打爆进度通道
            last_push = {"t": 0.0, "n": 0}

            async def _push_llm_delta(acc: str, _delta: str) -> None:
                now = time.perf_counter()
                if now - last_push["t"] < 0.05 and len(acc) - last_push["n"] < 12:
                    return
                last_push["t"] = now
                last_push["n"] = len(acc)
                # 模型正在返回 JSON，但教师端只展示业务进度；原始协议数据不得透出。
                preview = _agent_progress_text(current_agent)
                await _publish_state(
                    task_id,
                    agents_state,
                    overall_base,
                    current_agent,
                    step_results=step_results,
                    task_meta=task_meta,
                    stream={"agent": current_agent, "text": preview, "done": False},
                )

            if use_llm:
                data, summary, tokens = await _run_agent_llm(
                    db, agent, task, package, on_delta=_push_llm_delta
                )
            else:
                # Mock：边“生成”边流式打出结构化预览
                data, summary, tokens = _run_agent_mock(agent, task, package)
                package_tmp = merge_agent_output(dict(package), agent, data)
                if agent == "Reviewer":
                    score_package(package_tmp)
                focus_tmp = _package_focus(agent, package_tmp, data if isinstance(data, dict) else {"raw": data})
                await _stream_preview_text(
                    task_id,
                    agent,
                    focus_to_plain_text(agent, focus_tmp),
                    agents_state,
                    overall_base,
                    step_results,
                    task_meta,
                )

            package = merge_agent_output(package, agent, data)
            if agent == "PedagogyDesigner":
                adjusted = fit_teaching_flow_to_class_hours(
                    package,
                    int((task.config or {}).get("class_hours") or 2),
                )
                if adjusted:
                    data = {
                        "discussion_questions": package.get("discussion_questions", []),
                        "instructor_guide": package.get("instructor_guide", {}),
                        "alignment_matrix": package.get("alignment_matrix", []),
                    }
                    summary += "；授课流程已按课时自动校正"
            if agent == "CaseWriter":
                if use_llm:
                    package, repair_tokens = await _repair_casewriter_length(
                        db, task, package, on_delta=_push_llm_delta
                    )
                    tokens += repair_tokens
                else:
                    if not source_grounded and not contract_driven:
                        ensure_mock_body_length(package, task)

                actual = update_body_length_meta(package, task.target_words)
                minimum = math.ceil(task.target_words * 0.95)
                maximum = math.floor(task.target_words * 1.05)
                if not minimum <= actual <= maximum:
                    raise ValueError(
                        f"案例正文篇幅验收失败：实际 {actual} 字，"
                        f"要求 {minimum}–{maximum} 字（目标 {task.target_words} 字）"
                    )
                score_package(package)
                body = package.get("body") or {}
                data = {
                    "background": body.get("background"),
                    "narrative": body.get("narrative"),
                    "decision_point": body.get("decision_point"),
                    "characters": body.get("characters", []),
                }
                summary = f"案例正文已通过验收：实际 {actual} 字 / 目标 {task.target_words} 字"
            if agent == "Reviewer" and "overall_score" not in (package.get("quality") or {}):
                score_package(package)

            duration_ms = int((time.perf_counter() - t0) * 1000)
            focus = _package_focus(agent, package, data if isinstance(data, dict) else {"raw": data})
            completed_step = {
                "agent": agent,
                "status": "completed",
                "summary": summary,
                "focus": focus,
                "duration_ms": max(duration_ms, 1),
                "token_usage": tokens,
            }
            step_map[agent] = completed_step
            step_results = [s for s in step_results if s.get("agent") != agent]
            step_results.append(completed_step)

            db.add(
                AgentRunLog(
                    task_id=task_id,
                    agent_name=agent,
                    round=attempt_round,
                    input_summary=(
                        f"任务: {task.title}"
                        + " | Skills: "
                        + ", ".join(f"{item['name']}@{item['revision']}" for item in agent_skills)
                    ),
                    output_summary=summary,
                    token_usage=tokens,
                    duration_ms=max(duration_ms, 1),
                )
            )
            db.commit()

            agents_state = _build_agents_state(idx + 1, None, step_map=step_map)
            overall_now = int((idx + 1) / total * 100)
            # 完成后推送结构化过程预览（全文），并标记 done
            final_preview = focus_to_plain_text(agent, focus)
            await _publish_state(
                task_id,
                agents_state,
                overall_now,
                agent,
                step_results=step_results,
                task_meta=task_meta,
                stream={"agent": agent, "text": final_preview, "done": True},
            )
            # LLM 路径下再短暂停顿，便于用户看清该步结果
            if use_llm:
                await asyncio.sleep(0.6)

        actual = update_body_length_meta(package, task.target_words)
        minimum = math.ceil(task.target_words * 0.95)
        maximum = math.floor(task.target_words * 1.05)
        if not minimum <= actual <= maximum:
            raise ValueError(
                f"案例正文最终验收失败：实际 {actual} 字，要求 {minimum}–{maximum} 字"
            )

        if not package.get("quality") or not package["quality"].get("overall_score"):
            score_package(package)

        normalize_case_package(package)
        fit_teaching_flow_to_class_hours(
            package,
            int((task.config or {}).get("class_hours") or 2),
        )
        package.setdefault("meta", {})["skill_trace"] = skill_trace
        failure_stage = "quality_gate"
        validation = validate_package_with_skill(package, _task_context(task))
        current_narrative = str((package.get("body") or {}).get("narrative") or "")
        previous_packages = (
            db.query(CasePackage)
            .join(CaseTask, CaseTask.id == CasePackage.task_id)
            .filter(CaseTask.user_id == task.user_id, CaseTask.id != task.id)
            .order_by(CasePackage.created_at.desc())
            .limit(30)
            .all()
        )
        highest_similarity = 0.0
        similar_title = ""
        for previous in previous_packages:
            previous_narrative = str(((previous.package or {}).get("body") or {}).get("narrative") or "")
            similarity = text_similarity(current_narrative, previous_narrative)
            if similarity > highest_similarity:
                highest_similarity = similarity
                similar_title = str(((previous.package or {}).get("meta") or {}).get("title") or "历史案例")
        validation["cross_case_similarity"] = round(highest_similarity, 3)
        if highest_similarity >= 0.38:
            validation["issues"].append({
                "severity": "error", "code": "cross_case_template_similarity",
                "message": f"正文与《{similar_title}》高度相似（{highest_similarity:.0%}），疑似跨课程套壳",
                "path": "body.narrative",
            })
            validation["passed"] = False
        package.setdefault("quality", {})["validation"] = validation
        validation_errors = [
            issue["message"] for issue in validation["issues"] if issue.get("severity") == "error"
        ]
        if validation_errors:
            raise ValueError("案例包质量门禁未通过：" + "；".join(validation_errors))

        overall = float(package["quality"].get("overall_score") or 0)
        pkg = CasePackage(
            task_id=task_id,
            version=next_version,
            package=package,
            rubric_overall=overall,
            status="finalized" if overall >= settings.reviewer_pass_threshold else "draft",
        )
        db.add(pkg)

        task.status = "finalized" if overall >= settings.reviewer_pass_threshold else "completed"
        task.updated_at = datetime.now(timezone.utc)
        db.commit()

        final_agents = _build_agents_state(len(AGENT_SEQUENCE), None, step_map=step_map)
        await _publish_state(
            task_id,
            final_agents,
            100,
            "Reviewer",
            0,
            step_results=step_results,
            task_meta=task_meta,
        )

    except Exception as exc:  # noqa: BLE001
        # A failed flush leaves SQLAlchemy in pending-rollback state. Roll back
        # before persisting the task failure; otherwise the original failure is
        # masked and the task may remain stuck as running.
        db.rollback()
        task = db.query(CaseTask).filter(CaseTask.id == task_id).first()
        if not task:
            return
        task.status = "failed"
        task.error_message = str(exc)[:500]
        task.updated_at = datetime.now(timezone.utc)
        db.commit()
        failed_agents = _build_agents_state(len(step_map), None, step_map=step_map)
        if failure_stage == "agent_execution" and active_agent:
            for item in failed_agents:
                if item["name"] == active_agent and item["status"] != "completed":
                    item["status"] = "failed"
        await progress_hub.publish(
            task_id,
            {
                "type": "agent_progress",
                "task_id": task_id,
                "overall_progress": 99 if failure_stage == "quality_gate" else int(len(step_map) / len(AGENT_SEQUENCE) * 100),
                "current_agent": None,
                "agents": failed_agents,
                "step_results": step_results,
                "task_meta": task_meta,
                "error": str(exc),
                "failure_stage": failure_stage,
            },
        )


async def run_generation(db: Session, task_id: str) -> None:
    await run_pipeline(db, task_id)


def consume_quota(db: Session, user: User) -> None:
    if user.quota_remaining is not None and user.quota_remaining > 0:
        user.quota_remaining -= 1
        db.commit()
