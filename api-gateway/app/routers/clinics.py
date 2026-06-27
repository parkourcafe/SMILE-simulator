"""Partner clinics listing with optional geo-filtering (architecture §4.5)."""

from __future__ import annotations

from math import asin, cos, radians, sin, sqrt

from fastapi import APIRouter, Depends

from app.deps import CurrentUser, get_current_user
from app.schemas import ClinicOut
from app.services.supabase_client import get_supabase

router = APIRouter(prefix="/api/clinics", tags=["clinics"])


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
    dlat, dlng = radians(lat2 - lat1), radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    return round(2 * r * asin(sqrt(a)), 1)


@router.get("", response_model=list[ClinicOut])
async def list_clinics(
    city: str | None = None,
    lat: float | None = None,
    lng: float | None = None,
    radius_km: float | None = None,
    _: CurrentUser = Depends(get_current_user),
) -> list[ClinicOut]:
    sb = get_supabase()
    filters = {"status": "in.(active,trial)"}
    if city:
        filters["city"] = f"eq.{city}"
    rows = await sb.select("clinics", filters=filters)

    out: list[ClinicOut] = []
    for r in rows:
        distance = None
        if lat is not None and lng is not None and r.get("lat") and r.get("lng"):
            distance = _haversine_km(lat, lng, float(r["lat"]), float(r["lng"]))
            if radius_km is not None and distance > radius_km:
                continue
        out.append(
            ClinicOut(
                id=r["id"],
                name=r["name"],
                city=r["city"],
                address=r.get("address"),
                lat=r.get("lat"),
                lng=r.get("lng"),
                logo_url=r.get("logo_url"),
                specialties=r.get("specialties", []),
                distance_km=distance,
            )
        )
    out.sort(key=lambda c: (c.distance_km is None, c.distance_km or 0))
    return out
