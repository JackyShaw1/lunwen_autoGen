"""Deterministic objective suggestions shared by the API and teaching agents."""

from __future__ import annotations

from typing import Any


FRAMEWORK_META = {
    "pyramid": ("金字塔原理", "先形成核心判断，再用相互独立的论据支撑结论"),
    "systems": ("系统化思维", "识别要素与因果关系，再寻找高杠杆干预点"),
    "3w1h": ("3W1H", "从 Why、Who、What 到 How 形成完整行动闭环"),
}


def select_framework(title: str, case_type: str) -> str:
    text = f"{title}{case_type}"
    if case_type == "情境模拟" or any(word in text for word in ("实施", "落地", "沟通", "执行", "模拟")):
        return "3w1h"
    if case_type in ("分析型", "问题诊断") or any(
        word in text for word in ("原因", "机制", "影响", "系统", "生态", "阻力", "诊断")
    ):
        return "systems"
    return "pyramid"


def _subject_focus(subject: str) -> tuple[str, str, str]:
    focuses = {
        "管理学": ("利益相关者、资源与组织约束", "管理证据与关键矛盾", "组织实施与风险控制"),
        "经济学": ("激励、成本收益与市场约束", "数据证据与因果机制", "政策或经营方案及其外部性"),
        "计算机科学": ("用户需求、技术边界与系统约束", "架构证据、性能与安全风险", "技术方案、验证指标与迭代路径"),
        "法学": ("事实、主体关系与权利义务", "规则依据、争议焦点与论证链", "法律方案、程序选择与合规风险"),
    }
    return focuses.get(subject, ("关键参与者、资源与情境约束", "事实证据与核心矛盾", "解决方案与实施风险"))


def generate_objectives(context: dict[str, Any]) -> dict[str, Any]:
    title = str(context.get("title") or "课程主题").strip()
    subject = str(context.get("subject") or "相关学科").strip()
    course = str(context.get("course_name") or subject).strip()
    case_type = str(context.get("case_type") or "决策型").strip()
    audience = str(context.get("target_audience") or "本科").strip()
    difficulty = str(context.get("difficulty") or "中级").strip()
    variant = max(int(context.get("variant") or 0), 0)
    brief = context.get("objective_brief") or {}
    challenge = str(brief.get("learning_challenge") or "").strip()[:160]
    performance = str(brief.get("desired_performance") or "").strip()[:160]
    concepts = str(brief.get("required_concepts") or "").strip()[:160]
    assessment = str(brief.get("assessment_evidence") or "").strip()[:160]
    framework = select_framework(title, case_type)
    framework_name, rationale = FRAMEWORK_META[framework]
    actors, evidence, action = _subject_focus(subject)
    verbs = {
        "初级": ("识别", "解释", "提出"),
        "中级": ("分析", "评价", "设计"),
        "高级": ("建构", "论证", "整合设计"),
    }.get(difficulty, ("分析", "评价", "设计"))
    v1, v2, v3 = verbs

    variants = {
        "pyramid": [
            [f"{v1}“{title}”中的核心问题，并从{actors}中区分结论、事实与假设。", f"{v2}至少两种备选判断，运用{course}概念建立“结论—论据—证据”的金字塔结构。", f"{v3}一项针对“{title}”的决策建议，用独立理由、验证指标和风险回应清晰论证。"],
            [f"{v1}“{title}”的中心问题，将{evidence}归纳为三个相互独立的判断维度。", f"{v2}不同角色的支持与反对理由，判断论据是否充分且能够支撑结论。", f"{v3}面向{audience}课堂汇报的结构化建议，做到结论先行并回应关键反证。"],
            [f"{v1}“{title}”的主要矛盾，用一句可讨论结论统领{evidence}。", f"{v2}备选方案在目标、约束和风险上的差异，形成无重复遗漏的比较框架。", f"{v3}可执行的{action}，并定义用于课堂质询的验证标准。"],
        ],
        "systems": [
            [f"{v1}“{title}”中的关键主体、资源、制度与环境变量，绘制因果关系。", f"{v2}{evidence}如何通过反馈回路造成当前结果，区分症状、直接原因与系统根因。", f"{v3}针对高杠杆点的{action}，预测短期、长期影响并设置副作用指标。"],
            [f"{v1}“{title}”的系统边界和利益相关者，说明不同角色目标为何产生张力。", f"{v2}至少两条因果链及其延迟效应，运用{course}概念解释问题为何反复出现。", f"{v3}分阶段干预方案，说明每项行动改变的系统关系和非预期后果。"],
            [f"{v1}“{title}”中的存量、流量、约束与反馈，建立可检验的系统图景。", f"{v2}不同证据对机制的解释力，识别局部最优带来的整体风险。", f"{v3}兼顾{actors}的组合策略，设置前置、过程和结果指标。"],
        ],
        "3w1h": [
            [f"{v1}推进“{title}”的 Why，说明价值、目标优先级及不行动的后果。", f"{v2}Who 与 What，界定{actors}的诉求、责任和关键任务。", f"{v3}How，形成包含步骤、资源、节点、指标和风险预案的{action}。"],
            [f"{v1}“{title}”为何必须处理，并把课程概念转化为可衡量的情境目标。", f"{v2}谁影响结果、谁承担风险以及各方需要完成什么，建立责任矩阵。", f"{v3}可落地路径，明确顺序、沟通、阶段产出和复盘机制。"],
            [f"{v1}“{title}”的问题动因与成功标准，区分必要目标和可调整条件。", f"{v2}{actors}掌握的信息与所需行动，评价责任配置是否合理。", f"{v3}从试点到扩展的方案，用里程碑、责任人、资源和异常规则回答 How。"],
        ],
    }
    objectives = variants[framework][variant % len(variants[framework])]
    if challenge:
        objectives[0] = objectives[0].rstrip("。") + f"，重点解释“{challenge}”。"
    if concepts:
        objectives[1] = objectives[1].rstrip("。") + f"，并显式运用“{concepts}”形成证据链。"
    if performance or assessment:
        additions: list[str] = []
        if performance:
            additions.append(f"达到“{performance}”的课堂表现")
        if assessment:
            additions.append(f"以“{assessment}”作为可评价产出")
        objectives[2] = objectives[2].rstrip("。") + "，" + "，并".join(additions) + "。"

    checks = [
        {"key": "context", "label": "课程情境清楚", "passed": bool(title and course), "hint": "已由步骤1提供课程与案例主题"},
        {"key": "challenge", "label": "说明学生卡点", "passed": bool(challenge), "hint": "写学生目前只能做什么、还不会做什么"},
        {"key": "performance", "label": "描述课后表现", "passed": bool(performance), "hint": "使用分析、比较、论证、设计等可观察动作"},
        {"key": "concepts", "label": "指定知识方法", "passed": bool(concepts), "hint": "填写本课必须使用的概念、模型或思维工具"},
        {"key": "assessment", "label": "给出评价证据", "passed": bool(assessment), "hint": "例如决策备忘录、因果图、方案答辩或计算结果"},
    ]
    weights = {"context": 20, "challenge": 20, "performance": 25, "concepts": 20, "assessment": 15}
    quality_score = sum(weights[item["key"]] for item in checks if item["passed"])
    summary_parts = [
        f"面向{audience}《{course}》课程",
        f"解决“{challenge}”" if challenge else "围绕当前案例主题建立学习进阶",
        f"期望学生能够{performance}" if performance else "形成可观察的分析与决策能力",
        f"使用{concepts}" if concepts else f"使用{framework_name}",
        f"以{assessment}验收" if assessment else "通过课堂证据进行评价",
    ]
    return {
        "framework": framework,
        "framework_name": framework_name,
        "rationale": rationale,
        "objectives": objectives,
        "brief_summary": "；".join(summary_parts) + "。",
        "quality_score": quality_score,
        "quality_checks": checks,
    }


def validate_objectives(objectives: list[str]) -> list[str]:
    errors: list[str] = []
    if len(objectives) != 3:
        errors.append("教学目标必须恰好为 3 条")
    vague = ("了解", "熟悉", "掌握")
    for index, objective in enumerate(objectives, 1):
        if not str(objective).strip():
            errors.append(f"第 {index} 条教学目标为空")
        if any(word in str(objective) for word in vague):
            errors.append(f"第 {index} 条教学目标使用了不可观察动词")
    return errors
