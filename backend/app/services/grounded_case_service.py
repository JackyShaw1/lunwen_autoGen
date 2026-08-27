"""Teacher-constraint parsing and curated source-grounded case selection."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


PROFILE_PATH = Path(__file__).resolve().parent.parent / "materials" / "grounded_case_profiles.yaml"
STRICT_AUTHENTICITY_TERMS = (
    "不能虚假", "不得虚构", "禁止虚构", "不允许虚构", "切忌编造", "不要编造", "禁止编造",
    "不要胡编乱造", "胡编乱造", "数据准确", "真实案例", "真实企业案例", "基于真实企业", "事实准确",
)


def _compact(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or "")).lower()


def task_requirement_text(task: Any) -> str:
    objectives = getattr(task, "learning_objectives", None) or []
    config = getattr(task, "config", None) or {}
    return " ".join(str(value) for value in [*objectives, config.get("special_requirements", "")])


def requires_source_grounding(task: Any) -> bool:
    text = _compact(task_requirement_text(task))
    return any(_compact(term) in text for term in STRICT_AUTHENTICITY_TERMS)


@lru_cache(maxsize=1)
def load_grounded_profiles() -> list[dict[str, Any]]:
    return yaml.safe_load(PROFILE_PATH.read_text(encoding="utf-8")) or []


def find_grounded_profile(task: Any) -> dict[str, Any] | None:
    title = _compact(getattr(task, "title", ""))
    course = _compact(getattr(task, "course_name", ""))
    requirements = _compact(task_requirement_text(task))
    for profile in load_grounded_profiles():
        if not all(_compact(term) in title for term in profile.get("title_keywords") or []):
            continue
        if not all(_compact(term) in course for term in profile.get("course_keywords") or []):
            continue
        if not all(_compact(term) in requirements for term in profile.get("requirement_keywords") or []):
            continue
        supported_words = int(profile.get("supported_target_words") or 0)
        target_words = int(getattr(task, "target_words", 0) or 0)
        if supported_words and target_words and supported_words != target_words:
            continue
        return profile
    return None


def generation_preflight_error(task: Any) -> str | None:
    if requires_source_grounding(task) and not find_grounded_profile(task):
        return (
            "教师要求案例不得虚构，但当前课程尚无经过来源审核的事实资料包。"
            "系统已停止生成以避免编造；请先补充权威来源或由管理员完成课程资料审核。"
        )
    return None
