"""Payment webhooks (architecture §4.3, §7.2).

Security requirements:
  - Verify the provider signature (HMAC) before trusting the body.
  - Idempotency: process each provider_payment_id exactly once (the unique constraint
    on payments(provider, provider_payment_id) is the backstop).
  - Never lose a payment: on activation failure, the row stays and can be retried.
"""

from __future__ import annotations

import hashlib
import hmac
import logging

from fastapi import APIRouter, HTTPException, Request

from app.config import get_settings
from app.services.catalog import PACKS
from app.services.supabase_client import get_supabase

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])
log = logging.getLogger("smile.webhooks")


def _verify_hmac(secret: str, body: bytes, signature: str | None) -> bool:
    if not secret or not signature:
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


async def _activate_pack(user_id: str, pack_type: str, payment_id: str) -> None:
    sb = get_supabase()
    pack_def = PACKS.get(pack_type)
    if not pack_def:
        log.error("unknown pack_type %s for payment %s", pack_type, payment_id)
        return
    pack = await sb.insert(
        "packs",
        {
            "user_id": user_id,
            "pack_type": pack_type,
            "generations_total": pack_def.generations_total,
            "generations_used": 0,
            "price_amount": pack_def.price_rub,
            "price_currency": "RUB",
        },
    )
    await sb.update(
        "payments",
        filters={"id": f"eq.{payment_id}"},
        patch={"status": "completed", "pack_id": pack["id"], "completed_at": "now()"},
    )


@router.post("/yookassa")
async def yookassa_webhook(request: Request) -> dict:
    settings = get_settings()
    body = await request.body()
    signature = request.headers.get("X-Yookassa-Signature")
    if settings.is_production and not _verify_hmac(settings.yookassa_secret_key, body, signature):
        raise HTTPException(status_code=401, detail="invalid_signature")

    payload = await request.json()
    event = payload.get("event")
    obj = payload.get("object", {})
    provider_payment_id = obj.get("id")
    if event != "payment.succeeded" or not provider_payment_id:
        return {"ok": True, "ignored": event}

    sb = get_supabase()
    # Idempotency: skip if we already recorded this external id as completed.
    existing = await sb.select(
        "payments",
        filters={"provider": "eq.yookassa", "provider_payment_id": f"eq.{provider_payment_id}"},
        limit=1,
    )
    if existing and existing[0]["status"] == "completed":
        return {"ok": True, "duplicate": True}

    metadata = obj.get("metadata", {})
    user_id = metadata.get("user_id")
    pack_type = metadata.get("pack_type")
    if existing:
        await sb.update(
            "payments",
            filters={"id": f"eq.{existing[0]['id']}"},
            patch={"provider_payment_id": provider_payment_id},
        )
        await _activate_pack(user_id, pack_type, existing[0]["id"])
    return {"ok": True}


@router.post("/click")
async def click_webhook(request: Request) -> dict:
    # TODO(phase-3): implement Click's prepare/complete two-step protocol + signature.
    log.info("click webhook received (not yet implemented)")
    return {"ok": True}
