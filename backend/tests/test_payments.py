from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.config import Settings
from app.deps import CurrentUser
from app.main import app
from app.routers import packs, webhooks
from app.schemas import PurchaseRequest

USER_ID = "00000000-0000-0000-0000-000000000001"
PAYMENT_ID = "10000000-0000-0000-0000-000000000001"
IDEMPOTENCY_KEY = UUID("20000000-0000-0000-0000-000000000001")
PROVIDER_ID = "2fdd9000-000f-5000-a000-123456789abc"
PACK_ID = "50000000-0000-0000-0000-000000000001"


def _payment(**overrides):
    row = {
        "id": PAYMENT_ID,
        "user_id": USER_ID,
        "pack_type": "mini",
        "amount": "149.00",
        "currency": "RUB",
        "provider": "yookassa",
        "provider_payment_id": None,
        "provider_status": "pending",
        "idempotency_key": str(IDEMPOTENCY_KEY),
        "status": "pending",
        "confirmation_url": None,
        "pack_id": None,
    }
    row.update(overrides)
    return row


def _provider_payment(**overrides):
    row = {
        "id": PROVIDER_ID,
        "status": "succeeded",
        "paid": True,
        "amount": {"value": "149.00", "currency": "RUB"},
        "metadata": {
            "payment_id": PAYMENT_ID,
            "user_id": USER_ID,
            "pack_type": "mini",
        },
    }
    row.update(overrides)
    return row


class PaymentSupabase:
    configured = True

    def __init__(self, existing=None):
        self.payment = existing
        self.inserts = []
        self.updates = []
        self.rpc_calls = []

    async def select(self, table, *, filters=None, limit=None):
        if table == "payments":
            return [self.payment] if self.payment else []
        if table == "users":
            return [{"id": USER_ID, "free_gens_used": 1}]
        if table == "packs":
            return []
        raise AssertionError(table)

    async def insert(self, table, row):
        assert table == "payments"
        self.inserts.append(row)
        self.payment = {**row, "pack_id": None, "confirmation_url": None}
        return self.payment

    async def update(self, table, *, filters, patch):
        assert table == "payments"
        self.updates.append(patch)
        if self.payment:
            self.payment.update(patch)
        return [self.payment]

    async def rpc(self, function, params):
        self.rpc_calls.append((function, params))
        if self.payment:
            self.payment.update(status="completed", pack_id=PACK_ID)
        return {"activated": True, "duplicate": False, "pack_id": PACK_ID}


@pytest.mark.asyncio
async def test_mock_purchase_activates_once_through_database_rpc(monkeypatch):
    sb = PaymentSupabase()
    monkeypatch.setattr(packs, "get_supabase", lambda: sb)
    monkeypatch.setattr(packs, "get_settings", lambda: Settings(mock_payments=True))
    monkeypatch.setattr(packs, "uuid4", lambda: UUID(PAYMENT_ID))

    response = await packs.purchase(
        PurchaseRequest(pack_type="mini", provider="yookassa"),
        IDEMPOTENCY_KEY,
        CurrentUser(id=USER_ID),
    )

    assert response.payment_id == UUID(PAYMENT_ID)
    assert response.status == "completed"
    assert response.payment_url is None
    assert len(sb.inserts) == 1
    assert sb.rpc_calls == [
        (
            "activate_yookassa_payment",
            {
                "p_payment_id": PAYMENT_ID,
                "p_provider_payment_id": f"mock:{PAYMENT_ID}",
            },
        )
    ]


@pytest.mark.asyncio
async def test_real_purchase_returns_checkout_without_granting_pack(monkeypatch):
    sb = PaymentSupabase()
    provider = _provider_payment(
        status="pending",
        paid=False,
        confirmation={"confirmation_url": "https://yoomoney.ru/checkout/1"},
    )
    client = SimpleNamespace(create_payment=lambda **_kwargs: None)

    async def create_payment(**kwargs):
        client.kwargs = kwargs
        return provider

    client.create_payment = create_payment
    monkeypatch.setattr(packs, "get_supabase", lambda: sb)
    monkeypatch.setattr(
        packs,
        "get_settings",
        lambda: Settings(
            mock_payments=False,
            yookassa_shop_id="shop",
            yookassa_secret_key="secret",
            yookassa_return_url="https://www.zubilook.com/?payment=return",
        ),
    )
    monkeypatch.setattr(packs, "get_yookassa_client", lambda: client)
    monkeypatch.setattr(packs, "uuid4", lambda: UUID(PAYMENT_ID))

    response = await packs.purchase(
        PurchaseRequest(pack_type="mini", provider="yookassa"),
        IDEMPOTENCY_KEY,
        CurrentUser(id=USER_ID),
    )

    assert response.status == "pending"
    assert response.payment_url == "https://yoomoney.ru/checkout/1"
    assert not sb.rpc_calls
    assert sb.updates[-1]["provider_payment_id"] == PROVIDER_ID
    assert client.kwargs["idempotency_key"] == PAYMENT_ID
    assert client.kwargs["metadata"]["payment_id"] == PAYMENT_ID


@pytest.mark.asyncio
async def test_purchase_idempotency_reuses_checkout_and_rejects_changed_pack(monkeypatch):
    existing = _payment(confirmation_url="https://yoomoney.ru/checkout/1")
    sb = PaymentSupabase(existing)
    monkeypatch.setattr(packs, "get_supabase", lambda: sb)

    response = await packs.purchase(
        PurchaseRequest(pack_type="mini", provider="yookassa"),
        IDEMPOTENCY_KEY,
        CurrentUser(id=USER_ID),
    )
    assert response.payment_url == "https://yoomoney.ru/checkout/1"
    assert not sb.inserts

    with pytest.raises(HTTPException) as reused:
        await packs.purchase(
            PurchaseRequest(pack_type="main", provider="yookassa"),
            IDEMPOTENCY_KEY,
            CurrentUser(id=USER_ID),
        )
    assert reused.value.status_code == 409


def test_verified_webhook_activates_and_forged_status_is_rejected(monkeypatch):
    payment = _payment(provider_payment_id=PROVIDER_ID)
    sb = PaymentSupabase(payment)
    provider_client = SimpleNamespace()

    async def succeeded(_provider_id):
        return _provider_payment()

    provider_client.get_payment = succeeded
    monkeypatch.setattr(webhooks, "get_supabase", lambda: sb)
    monkeypatch.setattr(webhooks, "get_yookassa_client", lambda: provider_client)
    client = TestClient(app)

    response = client.post(
        "/v1/api/webhooks/yookassa",
        json={"type": "notification", "event": "payment.succeeded", "object": {"id": PROVIDER_ID}},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert len(sb.rpc_calls) == 1

    async def still_pending(_provider_id):
        return _provider_payment(status="pending", paid=False)

    provider_client.get_payment = still_pending
    forged = client.post(
        "/v1/api/webhooks/yookassa",
        json={"type": "notification", "event": "payment.succeeded", "object": {"id": PROVIDER_ID}},
    )
    assert forged.status_code == 409
    assert forged.json()["detail"] == "payment_status_mismatch"


@pytest.mark.asyncio
async def test_payment_status_recovers_a_missed_success_webhook(monkeypatch):
    sb = PaymentSupabase(_payment(provider_payment_id=PROVIDER_ID))
    provider_client = SimpleNamespace()

    async def succeeded(_provider_id):
        return _provider_payment()

    provider_client.get_payment = succeeded
    monkeypatch.setattr(packs, "get_supabase", lambda: sb)
    monkeypatch.setattr(packs, "get_yookassa_client", lambda: provider_client)
    monkeypatch.setattr(packs, "get_settings", lambda: Settings(mock_payments=False))

    result = await packs.payment_status(UUID(PAYMENT_ID), CurrentUser(id=USER_ID))

    assert result.status == "completed"
    assert result.pack_id == UUID(PACK_ID)
    assert len(sb.rpc_calls) == 1


def test_cancel_notification_cannot_regress_a_completed_payment(monkeypatch):
    payment = _payment(
        provider_payment_id=PROVIDER_ID,
        provider_status="succeeded",
        status="completed",
        pack_id=PACK_ID,
    )
    sb = PaymentSupabase(payment)
    provider_client = SimpleNamespace()

    async def canceled(_provider_id):
        return _provider_payment(status="canceled", paid=False)

    provider_client.get_payment = canceled
    monkeypatch.setattr(webhooks, "get_supabase", lambda: sb)
    monkeypatch.setattr(webhooks, "get_yookassa_client", lambda: provider_client)

    response = TestClient(app).post(
        "/v1/api/webhooks/yookassa",
        json={"type": "notification", "event": "payment.canceled", "object": {"id": PROVIDER_ID}},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "payment_state_conflict"
    assert payment["status"] == "completed"


@pytest.mark.asyncio
async def test_entitlements_ignore_expired_packs(monkeypatch):
    class EntitlementSupabase(PaymentSupabase):
        async def select(self, table, *, filters=None, limit=None):
            if table == "users":
                return [{"id": USER_ID, "free_gens_used": 1}]
            if table == "packs":
                return [
                    {
                        "generations_total": 20,
                        "generations_used": 3,
                        "expires_at": "2099-01-01T00:00:00Z",
                    },
                    {
                        "generations_total": 50,
                        "generations_used": 0,
                        "expires_at": "2000-01-01T00:00:00Z",
                    },
                ]
            raise AssertionError(table)

    monkeypatch.setattr(packs, "get_supabase", lambda: EntitlementSupabase())
    result = await packs.entitlements(CurrentUser(id=USER_ID))
    assert result.free_remaining == 0
    assert result.pack_remaining == 17
