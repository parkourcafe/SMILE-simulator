"""Generation quota logic: free tier (1, watermarked) + paid packs.

Returns whether a user may generate, whether the result must be watermarked, and
which pack (if any) to decrement. Decrementing itself is done by the caller after a
successful generation so a failed inference does not consume quota.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.config import get_settings
from app.services.supabase_client import SupabaseClient


@dataclass
class QuotaDecision:
    allowed: bool
    watermark: bool
    pack_id: str | None  # pack to decrement, or None for the free tier
    reason: str | None = None


async def evaluate(sb: SupabaseClient, user_id: str) -> QuotaDecision:
    settings = get_settings()

    # Prefer an active pack with remaining generations (no watermark).
    packs = await sb.select("packs", filters={"user_id": f"eq.{user_id}"})
    for pack in packs:
        if pack["generations_used"] < pack["generations_total"]:
            return QuotaDecision(allowed=True, watermark=False, pack_id=pack["id"])

    # Otherwise fall back to the free tier (watermarked, capped).
    users = await sb.select("users", filters={"id": f"eq.{user_id}"}, limit=1)
    free_used = users[0]["free_gens_used"] if users else 0
    if free_used < settings.free_generations:
        return QuotaDecision(allowed=True, watermark=True, pack_id=None)

    return QuotaDecision(allowed=False, watermark=False, pack_id=None, reason="limit_reached")


async def consume(sb: SupabaseClient, user_id: str, decision: QuotaDecision) -> None:
    """Decrement the chosen quota source after a successful generation."""
    if decision.pack_id:
        rows = await sb.select("packs", filters={"id": f"eq.{decision.pack_id}"}, limit=1)
        used = (rows[0]["generations_used"] if rows else 0) + 1
        await sb.update(
            "packs", filters={"id": f"eq.{decision.pack_id}"}, patch={"generations_used": used}
        )
    else:
        rows = await sb.select("users", filters={"id": f"eq.{user_id}"}, limit=1)
        used = (rows[0]["free_gens_used"] if rows else 0) + 1
        await sb.update("users", filters={"id": f"eq.{user_id}"}, patch={"free_gens_used": used})
