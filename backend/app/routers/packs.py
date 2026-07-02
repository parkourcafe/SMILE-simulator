"""Packs & payments (architecture §4.3).

Web checkout first (YooKassa) to avoid Apple/Google's 15–30% cut (architecture §7.1).
Actual provider-side payment creation is a TODO until merchant credentials exist; the
endpoint creates a pending payment row and returns a placeholder checkout URL so the
client flow can be built and tested end-to-end.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.config import get_settings
from app.deps import CurrentUser, get_current_user
from app.routers.webhooks import activate_pack
from app.schemas import MyPackOut, PackOption, PurchaseRequest, PurchaseResponse
from app.services.catalog import PACKS, price_for
from app.services.supabase_client import get_supabase

router = APIRouter(prefix="/api/packs", tags=["packs"])


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
            id=r["id"],
            pack_type=r["pack_type"],
            generations_total=r["generations_total"],
            generations_used=r["generations_used"],
            expires_at=r.get("expires_at"),
        )
        for r in rows
    ]


@router.post("/purchase", response_model=PurchaseResponse)
async def purchase(
    body: PurchaseRequest, user: CurrentUser = Depends(get_current_user)
) -> PurchaseResponse:
    if body.pack_type not in PACKS:
        raise HTTPException(status_code=404, detail="unknown_pack")

    currency = "UZS" if body.provider in {"click", "payme"} else "RUB"
    amount, cur = price_for(body.pack_type, currency)

    settings = get_settings()
    sb = get_supabase()
    payment = await sb.insert(
        "payments",
        {
            "user_id": user.id,
            "amount": amount,
            "currency": cur,
            "provider": body.provider,
            # Provisional id; replaced with the real provider id on webhook confirmation.
            "provider_payment_id": f"pending:{user.id}:{body.pack_type}",
            "status": "pending",
        },
    )

    base = settings.api_base_url
    if settings.mock_payments:
        # MOCK_PAYMENTS: no real provider call. Simulate an instantly-succeeded payment
        # so the pack unlocks and the client flow is testable end-to-end. The REAL
        # webhook path (signature verify + idempotency) is still exercised by fixtures.
        await activate_pack(user.id, body.pack_type, payment["id"])
        checkout_url = f"{base}/checkout/mock?payment_id={payment['id']}&status=succeeded"
        return PurchaseResponse(payment_id=payment["id"], payment_url=checkout_url)

    # TODO(phase-3, SELENA): create the real payment at YooKassa/Click and return its URL.
    checkout_url = f"{base}/checkout/mock?payment_id={payment['id']}"
    return PurchaseResponse(payment_id=payment["id"], payment_url=checkout_url)
