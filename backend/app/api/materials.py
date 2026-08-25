from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from app.dependencies import get_current_user
from app.models import User
from app.services.material_service import (
    get_cached_material_image,
    get_official_material,
    search_official_materials,
)


router = APIRouter(prefix="/materials", tags=["materials"])


@router.get("/search")
def search_materials(
    q: str = Query(min_length=2, max_length=200),
    limit: int = Query(default=12, ge=1, le=30),
    _user: User = Depends(get_current_user),
):
    return {"query": q, "items": search_official_materials(q, limit)}


@router.get("/{asset_id}/image")
def material_image(asset_id: str):
    asset = get_official_material(asset_id)
    if not asset:
        raise HTTPException(404, "素材不存在")
    try:
        path = get_cached_material_image(asset_id)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"官方素材暂时无法获取：{exc}") from exc
    suffix = path.suffix.lower()
    media_type = "image/png" if suffix == ".png" else ("image/webp" if suffix == ".webp" else "image/jpeg")
    return FileResponse(path, media_type=media_type, headers={"Cache-Control": "public, max-age=86400"})
