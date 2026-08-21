"""Load application Skills and progressively select task-relevant references/scripts."""

from __future__ import annotations

import hashlib
import importlib.util
import re
from functools import lru_cache
from pathlib import Path
from types import ModuleType
from typing import Any

import yaml


SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"

_PATTERN_ROUTES = {
    "决策型": "decision-case.md",
    "问题诊断": "diagnostic-case.md",
    "分析型": "mechanism-analysis.md",
    "方案设计": "solution-design.md",
    "伦理两难": "ethical-dilemma.md",
    "情境模拟": "role-simulation.md",
}

_SUBJECT_ROUTES = {
    "管理学": "management.md",
    "管理与商科": "management.md",
    "经济学": "economics-finance.md",
    "经济与金融": "economics-finance.md",
    "计算机科学": "computer-information.md",
    "计算机与信息": "computer-information.md",
    "法学": "law-public-policy.md",
    "法学与公共管理": "law-public-policy.md",
    "工程技术": "engineering.md",
    "教育学": "education.md",
    "医学与健康": "health.md",
}

_INSTRUCTIONAL_REFERENCES = {
    "CasePlanner": ["bloom-taxonomy.md", "objective-writing.md"],
    "PedagogyDesigner": ["bloom-taxonomy.md", "discussion-ladder.md", "alignment-rules.md"],
    "Reviewer": ["discussion-ladder.md", "alignment-rules.md"],
}


def _safe_name(value: str) -> str:
    if (
        not value
        or value in {".", ".."}
        or Path(value).name != value
        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", value)
    ):
        raise ValueError(f"无效 Skill 资源名：{value}")
    return value


@lru_cache(maxsize=64)
def _read_text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def _parse_skill(skill_name: str) -> tuple[dict[str, Any], str, Path]:
    safe = _safe_name(skill_name)
    path = SKILLS_DIR / safe / "SKILL.md"
    if not path.exists():
        raise ValueError(f"Agent 引用了不存在的 Skill：{skill_name}")
    raw = _read_text(str(path))
    if not raw.startswith("---\n") or "\n---\n" not in raw[4:]:
        raise ValueError(f"Skill frontmatter 无效：{skill_name}")
    header, body = raw[4:].split("\n---\n", 1)
    meta = yaml.safe_load(header) or {}
    if meta.get("name") != skill_name:
        raise ValueError(f"Skill 名称与目录不一致：{skill_name}")
    return meta, body.strip(), path.parent


def _select_references(skill_name: str, agent: str, task_context: dict[str, Any]) -> list[str]:
    if skill_name == "design-instructional-plan":
        return _INSTRUCTIONAL_REFERENCES.get(agent, [])
    if skill_name == "validate-case-package":
        return ["quality-rubric.md"]
    if skill_name == "apply-case-pattern":
        case_type = str(task_context.get("case_type") or "决策型")
        return [_PATTERN_ROUTES.get(case_type, "decision-case.md")]
    if skill_name == "adapt-subject-context":
        subject = str(task_context.get("subject") or "管理学")
        return [_SUBJECT_ROUTES.get(subject, "management.md")]
    return []


def build_agent_skill_context(
    agent: str,
    config: dict[str, Any],
    task_context: dict[str, Any],
) -> tuple[str, list[dict[str, Any]]]:
    sections: list[str] = []
    manifest: list[dict[str, Any]] = []
    for skill_name in config.get("skills") or []:
        meta, body, skill_dir = _parse_skill(str(skill_name))
        references = _select_references(str(skill_name), agent, task_context)
        content_parts = [body]
        for reference in references:
            safe_reference = _safe_name(reference)
            ref_path = skill_dir / "references" / safe_reference
            if not ref_path.exists():
                raise ValueError(f"Skill {skill_name} 缺少参考文件：{reference}")
            content_parts.append(_read_text(str(ref_path)))
        combined = "\n\n".join(content_parts)
        digest = hashlib.sha256(combined.encode("utf-8")).hexdigest()[:12]
        sections.append(f"## 已加载 Skill：{meta['name']}\n\n{combined}")
        manifest.append({"name": meta["name"], "revision": digest, "references": references})
    return "\n\n".join(sections), manifest


@lru_cache(maxsize=16)
def load_skill_script(skill_name: str, script_name: str) -> ModuleType:
    safe_skill = _safe_name(skill_name)
    safe_script = _safe_name(script_name)
    path = SKILLS_DIR / safe_skill / "scripts" / safe_script
    if not path.exists():
        raise ValueError(f"Skill {skill_name} 缺少脚本：{script_name}")
    module_name = f"case_skill_{safe_skill.replace('-', '_')}_{safe_script.replace('.', '_')}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载 Skill 脚本：{path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_package_with_skill(package: dict[str, Any], task_context: dict[str, Any]) -> dict[str, Any]:
    module = load_skill_script("validate-case-package", "validate_case_package.py")
    return module.validate_case_package(package, task_context)
