"""Curated course-scoped videos from official or highly trusted publishers."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


CATALOG_PATH = Path(__file__).resolve().parent.parent / "materials" / "official_videos.yaml"


def _compact(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or "")).lower()


@lru_cache(maxsize=1)
def load_official_videos() -> list[dict[str, Any]]:
    rows = yaml.safe_load(CATALOG_PATH.read_text(encoding="utf-8")) or []
    result: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["course_tags"] = [str(value) for value in item.get("course_tags") or []]
        item["keywords"] = [str(value) for value in item.get("keywords") or []]
        if item.get("published_at") is not None:
            item["published_at"] = str(item["published_at"])
        result.append(item)
    return result


def search_official_videos(query: str, limit: int = 10) -> list[dict[str, Any]]:
    normalized = _compact(query)
    ranked: list[tuple[int, dict[str, Any]]] = []
    for item in load_official_videos():
        course_matches = [value for value in item["course_tags"] if _compact(value) in normalized]
        keyword_matches = [value for value in item["keywords"] if _compact(value) in normalized]
        if not course_matches and not keyword_matches:
            continue
        score = 20 * len(set(course_matches)) + 8 * len(set(keyword_matches))
        ranked.append((score, {**item, "match_reasons": list(dict.fromkeys([*course_matches, *keyword_matches]))[:3]}))
    ranked.sort(key=lambda pair: (-pair[0], pair[1]["title"]))
    return [item for _, item in ranked[: max(1, min(limit, 20))]]


def recommended_videos(context: str, limit: int = 10) -> list[dict[str, Any]]:
    return search_official_videos(context, limit)
