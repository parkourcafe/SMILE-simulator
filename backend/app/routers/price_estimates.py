"""Cost-estimate anchor (v1.1, architecture §4 / UX rules).

Powers the result-screen block "Такая улыбка в {city}: {range}" and the
"learn the exact price at a nearby clinic" CTA. Numbers are team estimates
(``is_estimate=true``) until validated against real clinic pricing.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from app.deps import CurrentUser, get_current_user
from app.schemas import PriceEstimateOut
from app.services.supabase_client import get_supabase

router = APIRouter(prefix="/api/price-estimates", tags=["price-estimates"])


@router.get("", response_model=list[PriceEstimateOut])
async def list_price_estimates(
    city: str | None = None,
    style_id: UUID | None = None,
    _: CurrentUser = Depends(get_current_user),
) -> list[PriceEstimateOut]:
    sb = get_supabase()
    filters: dict[str, str] = {"is_active": "eq.true", "order": "sort_order.asc"}
    if city:
        filters["city"] = f"eq.{city}"
    if style_id:
        filters["style_id"] = f"eq.{style_id}"
    rows = await sb.select("price_estimates", filters=filters)
    return [
        PriceEstimateOut(
            id=r["id"],
            city=r["city"],
            style_id=r.get("style_id"),
            treatment_label=r["treatment_label"],
            treatment_label_ru=r["treatment_label_ru"],
            price_min=float(r["price_min"]),
            price_max=float(r["price_max"]),
            currency=r["currency"],
            is_estimate=r.get("is_estimate", True),
        )
        for r in rows
    ]
