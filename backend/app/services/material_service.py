"""Curated official visual materials with provenance and safe local caching."""

from __future__ import annotations

import hashlib
import re
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
import yaml

from app.config import settings


CATALOG_PATH = Path(__file__).resolve().parent.parent / "materials" / "official_visuals.yaml"
ALLOWED_IMAGE_HOSTS = {
    "media.ctg.com.cn", "www.ctg.com.cn", "ctg.com.cn", "dam.nea.gov.cn",
    "www.chizhou.gov.cn", "www.shanghai.gov.cn", "www.yidaiyilu.gov.cn",
    "www.news.cn", "sciencep.cas.cn",
    "www.cmse.gov.cn", "statistics.cmse.gov.cn",
}
MAX_IMAGE_BYTES = 8 * 1024 * 1024
GENERIC_KEYWORDS = {
    "管理", "管理学", "项目", "项目管理", "风险", "风险管理", "工程管理",
    "分析", "决策", "企业", "课程", "案例", "教学", "系统", "流程",
}


@lru_cache(maxsize=1)
def load_official_materials() -> list[dict[str, Any]]:
    data = yaml.safe_load(CATALOG_PATH.read_text(encoding="utf-8")) or []
    result: list[dict[str, Any]] = []
    for item in data:
        asset = dict(item)
        asset["keywords"] = [str(value) for value in asset.get("keywords") or []]
        asset["course_tags"] = [str(value) for value in asset.get("course_tags") or []]
        asset["exclude_keywords"] = [str(value) for value in asset.get("exclude_keywords") or []]
        if asset.get("published_at") is not None:
            asset["published_at"] = str(asset["published_at"])
        asset["official"] = True
        asset["preview_url"] = f"/api/materials/{asset['id']}/image"
        result.append(asset)
    return result


def get_official_material(asset_id: str) -> dict[str, Any] | None:
    return next((item for item in load_official_materials() if item["id"] == asset_id), None)


def search_official_materials(query: str, limit: int = 12) -> list[dict[str, Any]]:
    normalized_query = re.sub(r"\s+", "", query or "").lower()
    tokens = [token.lower() for token in re.findall(r"[\w\u4e00-\u9fff]+", query or "") if token]
    ranked: list[tuple[int, dict[str, Any]]] = []
    for asset in load_official_materials():
        if any(re.sub(r"\s+", "", value).lower() in normalized_query for value in asset.get("exclude_keywords") or []):
            continue
        title = str(asset.get("title") or "").lower()
        haystack = " ".join([
            title,
            str(asset.get("caption") or "").lower(),
            " ".join(asset.get("keywords") or []).lower(),
        ])
        course_tags = [value for value in asset.get("course_tags") or [] if value]
        matched_course_tags = [
            value for value in course_tags
            if re.sub(r"\s+", "", value).lower() in normalized_query
        ]
        # A generated course-context query contains title, subject, course and case type
        # as separate segments. It must match the curated course scope. A short manual
        # query may still locate a specific asset by title/keyword (for example “船闸”).
        is_course_context = len(tokens) >= 3
        if is_course_context and not matched_course_tags:
            continue
        anchors = [
            value for value in [*course_tags, *(asset.get("keywords") or [])]
            if value and value.lower() not in GENERIC_KEYWORDS
        ]
        matched_anchors = [
            value for value in anchors
            if re.sub(r"\s+", "", value).lower() in normalized_query
        ]
        # Course relevance is a hard gate. Generic terms such as “管理” must never make an
        # unrelated Three Gorges image appear in another course.
        if not matched_anchors:
            continue

        score = sum(18 + min(len(value), 10) * 2 for value in set(matched_anchors))
        for token in tokens:
            if token in title:
                score += 8
            elif token in haystack:
                score += 3
        for course_tag in asset.get("course_tags") or []:
            if re.sub(r"\s+", "", course_tag).lower() in normalized_query:
                score += 12
        if score:
            result = dict(asset)
            result["match_reasons"] = list(dict.fromkeys(matched_anchors))[:3]
            ranked.append((score, result))
    ranked.sort(key=lambda pair: (-pair[0], pair[1]["title"]))
    return [dict(asset) for _, asset in ranked[: max(1, min(limit, 30))]]


def recommended_materials(context: str, limit: int = 10) -> list[dict[str, Any]]:
    return search_official_materials(context, limit=limit)


def material_context_signature(title: str, subject: str, course: str, case_type: str) -> str:
    normalized = "|".join(re.sub(r"\s+", "", str(value or "")).lower() for value in (title, subject, course, case_type))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def _cache_path(asset: dict[str, Any]) -> Path:
    parsed = urlparse(asset["image_url"])
    suffix = Path(parsed.path).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        suffix = ".img"
    digest = hashlib.sha256(asset["image_url"].encode("utf-8")).hexdigest()[:16]
    cache_dir = Path(settings.export_dir).parent / "material_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"{asset['id']}-{digest}{suffix}"


def get_cached_material_image(asset_id: str) -> Path:
    asset = get_official_material(asset_id)
    if not asset:
        raise KeyError("素材不存在")
    parsed = urlparse(asset["image_url"])
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_IMAGE_HOSTS:
        raise ValueError("素材图片不在官方来源白名单中")
    path = _cache_path(asset)
    if path.exists() and 0 < path.stat().st_size <= MAX_IMAGE_BYTES:
        return path

    with httpx.stream(
        "GET",
        asset["image_url"],
        timeout=15.0,
        follow_redirects=True,
        headers={"User-Agent": "CaseAutoGenSystem/1.0 educational-material-fetcher"},
    ) as response:
        response.raise_for_status()
        content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
        if content_type not in {"image/jpeg", "image/png", "image/webp"}:
            raise ValueError("官方素材返回的不是受支持图片")
        total = 0
        payload = bytearray()
        for chunk in response.iter_bytes():
            total += len(chunk)
            if total > MAX_IMAGE_BYTES:
                raise ValueError("官方素材图片超过 8MB 限制")
            payload.extend(chunk)
    path.write_bytes(bytes(payload))
    return path


def resolve_package_materials(package: dict[str, Any], limit: int = 10) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for selected in package.get("visual_assets") or []:
        asset_id = str(selected.get("id") or "") if isinstance(selected, dict) else ""
        official = get_official_material(asset_id)
        if official and asset_id not in seen:
            result.append(dict(official))
            seen.add(asset_id)
        if len(result) >= limit:
            break
    return result
