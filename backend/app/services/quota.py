"""Atomic generation-credit reservation through a service-only database function."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import get_settings
from app.services.supabase_client import SupabaseClient, SupabaseError


@dataclass(frozen=True)
class QuotaReservation:
    allowed: bool
    generation: dict | None = None
    reason: str | None = None


async def reserve_generation(
    sb: SupabaseClient,
    *,
    user_id: str,
    style_id: str,
    photo_consent_id: str,
    original_photo_path: str,
) -> QuotaReservation:
    """Reserve exactly one credit and create the generation row atomically."""
    settings = get_settings()
    result = await sb.rpc(
        "reserve_generation_quota",
        {
            "p_user_id": user_id,
            "p_style_id": style_id,
            "p_photo_consent_id": photo_consent_id,
            "p_original_photo_path": original_photo_path,
            "p_rate_limit": settings.rate_limit_per_minute,
        },
    )
    if not isinstance(result, dict) or not isinstance(result.get("allowed"), bool):
        raise SupabaseError("reserve_generation_quota returned an invalid response")
    generation = result.get("generation")
    if result["allowed"] and not isinstance(generation, dict):
        raise SupabaseError("reserve_generation_quota omitted the generation row")
    reason = result.get("reason")
    return QuotaReservation(
        allowed=result["allowed"],
        generation=generation,
        reason=reason if isinstance(reason, str) else None,
    )
