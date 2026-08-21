"""教学目标 Skill 的应用服务入口。"""

from __future__ import annotations

from typing import Any

from app.services.skill_loader import load_skill_script


def generate_objectives(context: dict[str, Any]) -> dict[str, Any]:
    module = load_skill_script("design-instructional-plan", "generate_objectives.py")
    result = module.generate_objectives(context)
    errors = module.validate_objectives(result.get("objectives") or [])
    if errors:
        raise ValueError("；".join(errors))
    return result
