"""Style listing (architecture §4.4)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.deps import CurrentUser, get_current_user
from app.schemas import StyleOut
from app.services.supabase_client import get_supabase

router = APIRouter(prefix="/api/styles", tags=["styles"])


@router.get("", response_model=list[StyleOut])
async def list_styles(_: CurrentUser = Depends(get_current_user)) -> list[StyleOut]:
    sb = get_supabase()
    rows = await sb.select("styles", filters={"is_active": "eq.true", "order": "sort_order.asc"})
    return [
        StyleOut(
            id=r["id"],
            name=r["name"],
            name_ru=r["name_ru"],
            thumbnail_url=r.get("thumbnail_url"),
            is_premium=r.get("is_premium", False),
            sort_order=r.get("sort_order", 0),
        )
        for r in rows
    ]
