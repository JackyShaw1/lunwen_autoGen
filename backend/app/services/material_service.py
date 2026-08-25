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
ALLOWED_IMAGE_HOSTS = {"media.ctg.com.cn", "www.ctg.com.cn", "ctg.com.cn", "dam.nea.gov.cn"}
MAX_IMAGE_BYTES = 8 * 1024 * 1024


@lru_cache(maxsize=1)
def load_official_materials() -> list[dict[str, Any]]:
    data = yaml.safe_load(CATALOG_PATH.read_text(encoding="utf-8")) or []
    result: list[dict[str, Any]] = []
    for item in data:
        asset = dict(item)
        asset["keywords"] = [str(value) for value in asset.get("keywords") or []]
        if asset.get("published_at") is not None:
            asset["published_at"] = str(asset["published_at"])
        asset["official"] = True
        asset["preview_url"] = f"/api/materials/{asset['id']}/image"
        result.append(asset)
    return result


def get_official_material(asset_id: str) -> dict[str, Any] | None:
    return next((item for item in load_official_materials() if item["id"] == asset_id), None)


def search_official_materials(query: str, limit: int = 12) -> list[dict[str, Any]]:
    tokens = [token.lower() for token in re.findall(r"[\w\u4e00-\u9fff]+", query or "") if token]
    ranked: list[tuple[int, dict[str, Any]]] = []
    for asset in load_official_materials():
        title = str(asset.get("title") or "").lower()
        haystack = " ".join([
            title,
            str(asset.get("caption") or "").lower(),
            " ".join(asset.get("keywords") or []).lower(),
        ])
        score = 0
        for token in tokens:
            if token in title:
                score += 8
            elif token in haystack:
                score += 3
            # Chinese case titles are often long; match catalog keywords as substrings of the query.
            for keyword in asset.get("keywords") or []:
                if keyword.lower() in token or keyword.lower() in (query or "").lower():
                    score += 2
        if score:
            ranked.append((score, asset))
    ranked.sort(key=lambda pair: (-pair[0], pair[1]["title"]))
    return [dict(asset) for _, asset in ranked[: max(1, min(limit, 30))]]


def recommended_materials(context: str, limit: int = 3) -> list[dict[str, Any]]:
    return search_official_materials(context, limit=limit)


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


def resolve_package_materials(package: dict[str, Any], limit: int = 6) -> list[dict[str, Any]]:
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
