"""YAML 驱动的教学案例 Sequential 生成流水线（LLM 或结构化 Mock）"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Any

import yaml
from sqlalchemy.orm import Session

from app.config import get_settings, settings
from app.models import AgentConfig, AgentRunLog, CasePackage, CaseTask, User
from app.services.llm_client import chat_completion, extract_json, llm_available
from app.services.package_builder import build_structured_package, merge_agent_output
from app.services.progress_hub import progress_hub
from app.services.rubric_service import score_package

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
    )
    specs = {
        "CasePlanner": (
            "请输出 JSON，字段：outline{background,decision_point,characters[]}，"
            "learning_objectives[{id,level,description}]。"
        ),
        "DomainExpert": "请输出 JSON，字段：domain_notes(string)，characters(可选更新)。",
        "CaseWriter": (
            "请输出 JSON，字段：background, narrative, decision_point, characters[]。"
            f"叙事总字数约 {task.target_words} 字，适合课堂讨论。"
        ),
        "PedagogyDesigner": (
            "请输出 JSON，字段：discussion_questions[{level,question,teaching_intent}]（至少5题），"
            "instructor_guide{teaching_flow,key_points[],common_misconceptions[]}，"
            "alignment_matrix[{objective_id,case_section,activity,assessment}]。"
        ),
        "Reviewer": (
            "请输出 JSON，字段：rubric_scores{alignment,authenticity,discussion,structure,readability}，"
            "overall_score(1-5)，reviewer_summary，issues[]。"
        ),
    }
    return base + specs.get(agent, "请输出与教学案例相关的 JSON。")


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
    model_cfg = cfg.get("model") or {}
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": _agent_user_prompt(agent, task, package)},
    ]
    content = await chat_completion(
        messages,
        temperature=float(model_cfg.get("temperature", 0.7)),
        max_tokens=int(model_cfg.get("max_tokens", 4096)),
        model=settings.openai_model,
        on_delta=on_delta,
    )
    try:
        data = extract_json(content)
    except Exception:
        data = {"raw": content}
    if not isinstance(data, dict):
        data = {"raw": data}
    summary = content[:240].replace("\n", " ")
    tokens = max(len(content) // 3, 1)
    return data, summary, tokens


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
        data = {
            "domain_notes": (
                f"{task.subject}情境约束：术语使用需符合《{task.course_name}》教学语境，"
                "避免过度简化专业机制。"
            )
        }
        summary = "已补充学科情境与术语约束"
    elif agent == "CaseWriter":
        data = {
            "background": package["body"]["background"],
            "narrative": package["body"]["narrative"],
            "decision_point": package["body"]["decision_point"],
            "characters": package["body"]["characters"],
        }
        summary = f"已撰写案例正文（约 {task.target_words} 字目标）"
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
    """给前端右侧面板的可读切片，避免一次推送过大。"""
    body = package.get("body") or {}
    if agent == "CasePlanner":
        return {
            "learning_objectives": package.get("learning_objectives", []),
            "decision_point": body.get("decision_point"),
            "characters": body.get("characters", []),
            "agent_output": output,
        }
    if agent == "DomainExpert":
        return {
            "background": (body.get("background") or "")[:800],
            "domain_notes": output.get("domain_notes") or output.get("terminology"),
            "agent_output": output,
        }
    if agent == "CaseWriter":
        return {
            "background": (body.get("background") or "")[:600],
            "narrative": (body.get("narrative") or "")[:1200],
            "decision_point": body.get("decision_point"),
            "characters": body.get("characters", []),
            "agent_output": output,
        }
    if agent == "PedagogyDesigner":
        return {
            "discussion_questions": package.get("discussion_questions", []),
            "instructor_guide": package.get("instructor_guide", {}),
            "alignment_matrix": package.get("alignment_matrix", []),
            "agent_output": output,
        }
    if agent == "Reviewer":
        return {
            "quality": package.get("quality", {}),
            "agent_output": output,
        }
    return {"agent_output": output}


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


async def run_pipeline(db: Session, task_id: str, only_agent: str | None = None) -> None:
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
    }

    latest = (
        db.query(CasePackage)
        .filter(CasePackage.task_id == task_id)
        .order_by(CasePackage.version.desc())
        .first()
    )
    if only_agent and latest and latest.package:
        package = dict(latest.package)
        next_version = (latest.version or 1) + 1
    else:
        package = build_structured_package(task)
        next_version = (latest.version + 1) if latest else 1

    use_llm = llm_available()
    logger.warning(
        "generation mode task=%s use_llm=%s model=%s",
        task_id,
        use_llm,
        get_settings().openai_model if use_llm else "mock",
    )
    agents = [only_agent] if only_agent else list(AGENT_SEQUENCE)
    if only_agent and only_agent not in AGENT_SEQUENCE:
        task.status = "failed"
        task.error_message = f"未知 Agent: {only_agent}"
        db.commit()
        return

    total = len(AGENT_SEQUENCE)
    step_results: list[dict[str, Any]] = []
    step_map: dict[str, dict[str, Any]] = {}

    try:
        for step_i, agent in enumerate(agents):
            idx = AGENT_SEQUENCE.index(agent)
            # 标记当前 Agent 运行中，右侧可先显示任务输入
            running_step = {
                "agent": agent,
                "status": "running",
                "summary": AGENT_HINTS[agent],
                "input": {
                    "task": task_meta,
                    "hint": AGENT_HINTS[agent],
                },
                "output": None,
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
                preview = f"【{current_agent} 模型输出中】\n\n{acc}"
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
            if agent == "Reviewer" and "overall_score" not in (package.get("quality") or {}):
                score_package(package)

            duration_ms = int((time.perf_counter() - t0) * 1000)
            focus = _package_focus(agent, package, data if isinstance(data, dict) else {"raw": data})
            completed_step = {
                "agent": agent,
                "status": "completed",
                "summary": summary,
                "input": {"task": task_meta, "hint": AGENT_HINTS[agent]},
                "output": data if isinstance(data, dict) else {"raw": data},
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
                    round=1 if only_agent else 0,
                    input_summary=f"任务: {task.title}" + (f" | 局部重跑" if only_agent else ""),
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

        if not package.get("quality") or not package["quality"].get("overall_score"):
            score_package(package)

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
        task.status = "failed"
        task.error_message = str(exc)[:500]
        task.updated_at = datetime.now(timezone.utc)
        db.commit()
        await progress_hub.publish(
            task_id,
            {
                "type": "agent_progress",
                "task_id": task_id,
                "overall_progress": 0,
                "current_agent": None,
                "agents": [
                    {"name": n, "status": "failed" if n == AGENT_SEQUENCE[0] else "pending"}
                    for n in AGENT_SEQUENCE
                ],
                "step_results": step_results,
                "task_meta": task_meta,
                "error": str(exc),
            },
        )


async def run_generation(db: Session, task_id: str, only_agent: str | None = None) -> None:
    await run_pipeline(db, task_id, only_agent=only_agent)


def consume_quota(db: Session, user: User) -> None:
    if user.quota_remaining is not None and user.quota_remaining > 0:
        user.quota_remaining -= 1
        db.commit()
