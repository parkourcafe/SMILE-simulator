"""Pack catalog, server-authoritative entitlements, and YooKassa checkout."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException

from app.config import get_settings
from app.deps import CurrentUser, get_current_user
from app.schemas import (
    EntitlementsOut,
    MyPackOut,
    PackOption,
    PaymentStatusOut,
    PurchaseRequest,
    PurchaseResponse,
)
from app.services.catalog import PACKS, price_for
from app.services.payment_activation import activate_yookassa_payment
from app.services.supabase_client import SupabaseClient, SupabaseError, get_supabase
from app.services.yookassa import YooKassaError, get_yookassa_client

router = APIRouter(prefix="/api/packs", tags=["packs"])


def _public_payment_status(status: str) -> str:
    if status == "completed":
        return "completed"
    if status in {"failed", "refunded"}:
        return "failed"
    return "pending"


def _payment_response(row: dict) -> PurchaseResponse:
    status = _public_payment_status(row["status"])
    return PurchaseResponse(
        payment_id=row["id"],
        status=status,
        payment_url=row.get("confirmation_url") if status == "pending" else None,
    )


async def _payment_by_key(
    sb: SupabaseClient,
    *,
    user_id: str,
    idempotency_key: str,
) -> dict | None:
    rows = await sb.select(
        "payments",
        filters={
            "user_id": f"eq.{user_id}",
            "idempotency_key": f"eq.{idempotency_key}",
        },
        limit=1,
    )
    return rows[0] if rows else None


def _validate_provider_payment(
    provider_payment: dict,
    *,
    payment_id: str,
    user_id: str,
    pack_type: str,
    amount: Decimal,
    currency: str,
) -> None:
    try:
        provider_amount = Decimal(str(provider_payment["amount"]["value"]))
        provider_currency = provider_payment["amount"]["currency"]
        metadata = provider_payment["metadata"]
    except (KeyError, InvalidOperation, TypeError) as exc:
        raise YooKassaError("YooKassa payment payload is incomplete") from exc
    if provider_amount != amount or provider_currency != currency:
        raise YooKassaError("YooKassa payment amount does not match the intent")
    if not isinstance(metadata, dict) or metadata != {
        "payment_id": payment_id,
        "user_id": user_id,
        "pack_type": pack_type,
    }:
        raise YooKassaError("YooKassa payment metadata does not match the intent")


async def _reconcile_pending_payment(sb: SupabaseClient, row: dict) -> dict:
    """Recover completion when the provider webhook is delayed or was missed."""
    if row["status"] != "pending" or get_settings().mock_payments:
        return row
    provider_id = row.get("provider_payment_id")
    if not isinstance(provider_id, str) or not provider_id:
        return row

    try:
        provider_payment = await get_yookassa_client().get_payment(provider_id)
        if provider_payment.get("id") != provider_id:
            raise YooKassaError("YooKassa payment ID does not match the intent")
        _validate_provider_payment(
            provider_payment,
            payment_id=str(row["id"]),
            user_id=str(row["user_id"]),
            pack_type=row["pack_type"],
            amount=Decimal(str(row["amount"])),
            currency=row["currency"],
        )
    except (InvalidOperation, YooKassaError) as exc:
        raise HTTPException(status_code=503, detail="payment_verification_unavailable") from exc

    provider_status = provider_payment["status"]
    if provider_status == "succeeded":
        if provider_payment.get("paid") is not True:
            raise HTTPException(status_code=409, detail="payment_not_paid")
        await sb.update(
            "payments",
            filters={"id": f"eq.{row['id']}"},
            patch={"provider_status": "succeeded"},
        )
        activation = await activate_yookassa_payment(
            sb,
            payment_id=str(row["id"]),
            provider_payment_id=provider_id,
        )
        return {
            **row,
            "status": "completed",
            "provider_status": "succeeded",
            "pack_id": activation.get("pack_id") or row.get("pack_id"),
        }
    if provider_status == "canceled":
        await sb.update(
            "payments",
            filters={"id": f"eq.{row['id']}"},
            patch={"provider_status": "canceled", "status": "failed"},
        )
        return {**row, "status": "failed", "provider_status": "canceled"}
    return row


@router.get("/available", response_model=list[PackOption])
async def available(currency: str = "RUB") -> list[PackOption]:
    options = []
    for pack in PACKS.values():
        amount, cur = price_for(pack.pack_type, currency)
        options.append(
            PackOption(
                pack_type=pack.pack_type,
                generations_total=pack.generations_total,
                price_amount=amount,
                price_currency=cur,
                title=pack.title,
            )
        )
    return options


@router.get("/my", response_model=list[MyPackOut])
async def my_packs(user: CurrentUser = Depends(get_current_user)) -> list[MyPackOut]:
    sb = get_supabase()
    rows = await sb.select("packs", filters={"user_id": f"eq.{user.id}"})
    return [
        MyPackOut(
            id=row["id"],
            pack_type=row["pack_type"],
            generations_total=row["generations_total"],
            generations_used=row["generations_used"],
            expires_at=row.get("expires_at"),
        )
        for row in rows
    ]


@router.get("/entitlements", response_model=EntitlementsOut)
async def entitlements(user: CurrentUser = Depends(get_current_user)) -> EntitlementsOut:
    sb = get_supabase()
    users = await sb.select("users", filters={"id": f"eq.{user.id}"}, limit=1)
    if not users:
        raise HTTPException(status_code=409, detail="user_profile_not_ready")
    packs = await sb.select("packs", filters={"user_id": f"eq.{user.id}"})
    now = datetime.now(UTC)
    pack_remaining = 0
    for pack in packs:
        expires_at = pack.get("expires_at")
        if expires_at:
            expiry = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
            if expiry <= now:
                continue
        pack_remaining += max(
            int(pack["generations_total"]) - int(pack["generations_used"]),
            0,
        )
    return EntitlementsOut(
        free_remaining=max(1 - int(users[0]["free_gens_used"]), 0),
        pack_remaining=pack_remaining,
    )


@router.post("/purchase", response_model=PurchaseResponse)
async def purchase(
    body: PurchaseRequest,
    idempotency_key: UUID = Header(alias="Idempotency-Key"),
    user: CurrentUser = Depends(get_current_user),
) -> PurchaseResponse:
    if body.pack_type not in PACKS:
        raise HTTPException(status_code=404, detail="unknown_pack")

    sb = get_supabase()
    key = str(idempotency_key)
    existing = await _payment_by_key(sb, user_id=user.id, idempotency_key=key)
    if existing and (
        existing.get("pack_type") != body.pack_type or existing.get("provider") != body.provider
    ):
        raise HTTPException(status_code=409, detail="idempotency_key_reused")
    if existing and (existing["status"] != "pending" or existing.get("confirmation_url")):
        return _payment_response(existing)

    amount_float, currency = price_for(body.pack_type, "RUB")
    amount = Decimal(str(amount_float)).quantize(Decimal("0.01"))
    payment = existing
    if payment is None:
        payment_id = str(uuid4())
        row = {
            "id": payment_id,
            "user_id": user.id,
            "pack_type": body.pack_type,
            "amount": str(amount),
            "currency": currency,
            "provider": body.provider,
            "provider_payment_id": None,
            "provider_status": "pending",
            "idempotency_key": key,
            "status": "pending",
        }
        try:
            payment = await sb.insert("payments", row)
        except SupabaseError:
            payment = await _payment_by_key(sb, user_id=user.id, idempotency_key=key)
            if payment is None:
                raise

    settings = get_settings()
    if settings.mock_payments:
        provider_id = f"mock:{payment['id']}"
        await sb.update(
            "payments",
            filters={"id": f"eq.{payment['id']}"},
            patch={"provider_payment_id": provider_id, "provider_status": "succeeded"},
        )
        await activate_yookassa_payment(
            sb,
            payment_id=payment["id"],
            provider_payment_id=provider_id,
        )
        return PurchaseResponse(payment_id=payment["id"], status="completed")

    metadata = {
        "payment_id": payment["id"],
        "user_id": user.id,
        "pack_type": body.pack_type,
    }
    try:
        provider_payment = await get_yookassa_client().create_payment(
            # The client key deduplicates our intent. The local payment UUID is the
            # server-owned, shop-wide idempotency key sent to YooKassa.
            idempotency_key=str(payment["id"]),
            amount=amount,
            currency=currency,
            description=f"ZubiLook {PACKS[body.pack_type].title}",
            metadata=metadata,
        )
        _validate_provider_payment(
            provider_payment,
            payment_id=payment["id"],
            user_id=user.id,
            pack_type=body.pack_type,
            amount=amount,
            currency=currency,
        )
    except YooKassaError as exc:
        raise HTTPException(status_code=502, detail="payment_provider_unavailable") from exc

    provider_id = provider_payment["id"]
    provider_status = provider_payment["status"]
    confirmation_url = (provider_payment.get("confirmation") or {}).get("confirmation_url")
    if provider_status == "pending" and (
        not isinstance(confirmation_url, str) or not confirmation_url.startswith("https://")
    ):
        raise HTTPException(status_code=502, detail="payment_confirmation_missing")

    patch = {
        "provider_payment_id": provider_id,
        "provider_status": provider_status,
        "confirmation_url": confirmation_url,
    }
    if provider_status == "canceled":
        patch["status"] = "failed"
    await sb.update("payments", filters={"id": f"eq.{payment['id']}"}, patch=patch)

    if provider_status == "succeeded" and provider_payment.get("paid") is True:
        await activate_yookassa_payment(
            sb,
            payment_id=payment["id"],
            provider_payment_id=provider_id,
        )
        return PurchaseResponse(payment_id=payment["id"], status="completed")
    if provider_status == "canceled":
        return PurchaseResponse(payment_id=payment["id"], status="failed")
    if provider_status != "pending":
        raise HTTPException(status_code=502, detail="unexpected_payment_status")
    return PurchaseResponse(
        payment_id=payment["id"],
        status="pending",
        payment_url=confirmation_url,
    )


@router.get("/payments/{payment_id}", response_model=PaymentStatusOut)
async def payment_status(
    payment_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> PaymentStatusOut:
    sb = get_supabase()
    rows = await sb.select(
        "payments",
        filters={"id": f"eq.{payment_id}", "user_id": f"eq.{user.id}"},
        limit=1,
    )
    if not rows:
        raise HTTPException(status_code=404, detail="payment_not_found")
    row = await _reconcile_pending_payment(sb, rows[0])
    return PaymentStatusOut(
        payment_id=row["id"],
        status=_public_payment_status(row["status"]),
        pack_id=row.get("pack_id"),
    )
