"""Provider webhooks verified against current server-to-server payment state."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request

from app.services.payment_activation import activate_yookassa_payment
from app.services.supabase_client import get_supabase
from app.services.yookassa import YooKassaError, get_yookassa_client

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


def _metadata_payment_id(provider_payment: dict) -> str:
    metadata = provider_payment.get("metadata")
    if not isinstance(metadata, dict):
        raise HTTPException(status_code=409, detail="payment_metadata_missing")
    try:
        return str(UUID(str(metadata["payment_id"])))
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=409, detail="payment_metadata_invalid") from exc


def _verify_local_payment(row: dict, provider_payment: dict) -> None:
    metadata = provider_payment.get("metadata")
    amount = provider_payment.get("amount")
    try:
        provider_amount = Decimal(str(amount["value"]))
        local_amount = Decimal(str(row["amount"]))
        currency = amount["currency"]
    except (KeyError, TypeError, InvalidOperation) as exc:
        raise HTTPException(status_code=409, detail="payment_amount_invalid") from exc
    if (
        not isinstance(metadata, dict)
        or metadata.get("payment_id") != str(row["id"])
        or metadata.get("user_id") != str(row["user_id"])
        or metadata.get("pack_type") != row.get("pack_type")
        or provider_amount != local_amount
        or currency != row["currency"]
        or row["provider"] != "yookassa"
    ):
        raise HTTPException(status_code=409, detail="payment_intent_mismatch")
    existing_provider_id = row.get("provider_payment_id")
    if existing_provider_id and existing_provider_id != provider_payment["id"]:
        raise HTTPException(status_code=409, detail="provider_payment_mismatch")


@router.post("/yookassa")
async def yookassa_webhook(request: Request) -> dict:
    payload = await request.json()
    if not isinstance(payload, dict) or payload.get("type") != "notification":
        raise HTTPException(status_code=400, detail="invalid_notification")
    event = payload.get("event")
    if event not in {"payment.succeeded", "payment.canceled"}:
        return {"ok": True, "ignored": event}

    notification = payload.get("object")
    provider_payment_id = notification.get("id") if isinstance(notification, dict) else None
    if not isinstance(provider_payment_id, str) or not provider_payment_id:
        raise HTTPException(status_code=400, detail="payment_id_missing")

    try:
        provider_payment = await get_yookassa_client().get_payment(provider_payment_id)
    except YooKassaError as exc:
        # A non-200 response makes YooKassa retry the notification later.
        raise HTTPException(status_code=503, detail="payment_verification_unavailable") from exc
    if provider_payment.get("id") != provider_payment_id:
        raise HTTPException(status_code=409, detail="provider_payment_mismatch")

    expected_status = "succeeded" if event == "payment.succeeded" else "canceled"
    if provider_payment.get("status") != expected_status:
        raise HTTPException(status_code=409, detail="payment_status_mismatch")
    if expected_status == "succeeded" and provider_payment.get("paid") is not True:
        raise HTTPException(status_code=409, detail="payment_not_paid")

    payment_id = _metadata_payment_id(provider_payment)
    sb = get_supabase()
    rows = await sb.select("payments", filters={"id": f"eq.{payment_id}"}, limit=1)
    if not rows:
        raise HTTPException(status_code=404, detail="payment_not_found")
    payment = rows[0]
    _verify_local_payment(payment, provider_payment)

    if expected_status == "canceled":
        if payment["status"] == "completed":
            raise HTTPException(status_code=409, detail="payment_state_conflict")
        if payment["status"] in {"failed", "refunded"}:
            return {"ok": True, "status": "failed", "duplicate": True}
        await sb.update(
            "payments",
            filters={"id": f"eq.{payment_id}"},
            patch={
                "provider_payment_id": provider_payment_id,
                "provider_status": "canceled",
                "status": "failed",
            },
        )
        return {"ok": True, "status": "failed"}

    await sb.update(
        "payments",
        filters={"id": f"eq.{payment_id}"},
        patch={
            "provider_payment_id": provider_payment_id,
            "provider_status": "succeeded",
        },
    )
    activation = await activate_yookassa_payment(
        sb,
        payment_id=payment_id,
        provider_payment_id=provider_payment_id,
    )
    return {
        "ok": True,
        "status": "completed",
        "duplicate": bool(activation.get("duplicate")),
    }


@router.post("/click")
async def click_webhook(_request: Request) -> dict:
    # Click/Payme are post-MVP for the Uzbekistan launch. Fail closed until their
    # signed prepare/complete protocols are implemented and tested.
    raise HTTPException(status_code=501, detail="click_payments_not_implemented")
