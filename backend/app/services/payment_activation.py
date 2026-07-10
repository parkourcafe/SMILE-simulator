"""Atomic payment-to-pack activation through a service-only database function."""

from __future__ import annotations

from app.services.supabase_client import SupabaseClient, SupabaseError


async def activate_yookassa_payment(
    sb: SupabaseClient,
    *,
    payment_id: str,
    provider_payment_id: str,
) -> dict:
    result = await sb.rpc(
        "activate_yookassa_payment",
        {
            "p_payment_id": payment_id,
            "p_provider_payment_id": provider_payment_id,
        },
    )
    if not isinstance(result, dict) or not isinstance(result.get("activated"), bool):
        raise SupabaseError("activate_yookassa_payment returned an invalid response")
    if not result["activated"] and not result.get("duplicate"):
        raise SupabaseError(
            f"activate_yookassa_payment rejected payment: {result.get('reason', 'unknown')}"
        )
    return result
