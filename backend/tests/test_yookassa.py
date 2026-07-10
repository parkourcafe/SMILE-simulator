from __future__ import annotations

from decimal import Decimal

import httpx
import pytest

from app.config import Settings
from app.services import yookassa
from app.services.yookassa import YooKassaClient, YooKassaError


class Response:
    def __init__(self, body, status_code=200):
        self._body = body
        self.status_code = status_code

    def json(self):
        return self._body


@pytest.mark.asyncio
async def test_create_payment_uses_basic_auth_idempotency_and_redirect(monkeypatch):
    captured = {}
    body = {
        "id": "provider-payment-1",
        "status": "pending",
        "paid": False,
        "amount": {"value": "149.00", "currency": "RUB"},
        "confirmation": {
            "type": "redirect",
            "confirmation_url": "https://yoomoney.ru/checkout/1",
        },
        "metadata": {
            "payment_id": "local-payment-1",
            "user_id": "user-1",
            "pack_type": "mini",
        },
    }

    class Client:
        def __init__(self, *, auth, timeout):
            captured.update(auth=auth, timeout=timeout)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, url, *, headers, json):
            captured.update(url=url, headers=headers, json=json)
            return Response(body)

    monkeypatch.setattr(yookassa.httpx, "AsyncClient", Client)
    client = YooKassaClient(
        Settings(
            yookassa_shop_id="shop-1",
            yookassa_secret_key="secret-1",
            yookassa_return_url="https://www.zubilook.com/?payment=return",
        )
    )
    result = await client.create_payment(
        idempotency_key="40000000-0000-0000-0000-000000000001",
        amount=Decimal("149.00"),
        currency="RUB",
        description="ZubiLook Mini",
        metadata=body["metadata"],
    )

    assert result == body
    assert isinstance(captured["auth"], httpx.BasicAuth)
    assert captured["timeout"] == 30
    assert captured["url"] == "https://api.yookassa.ru/v3/payments"
    assert captured["headers"] == {"Idempotence-Key": "40000000-0000-0000-0000-000000000001"}
    assert captured["json"] == {
        "amount": {"value": "149.00", "currency": "RUB"},
        "capture": True,
        "confirmation": {
            "type": "redirect",
            "return_url": "https://www.zubilook.com/?payment=return",
        },
        "description": "ZubiLook Mini",
        "metadata": body["metadata"],
    }


@pytest.mark.asyncio
async def test_get_payment_and_provider_errors_fail_closed(monkeypatch):
    captured = {}

    class Client:
        def __init__(self, *, auth, timeout):
            captured.update(auth=auth, timeout=timeout)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def get(self, url):
            captured["url"] = url
            return Response({"type": "error"}, status_code=503)

    monkeypatch.setattr(yookassa.httpx, "AsyncClient", Client)
    client = YooKassaClient(Settings(yookassa_shop_id="shop-1", yookassa_secret_key="secret-1"))

    with pytest.raises(YooKassaError, match="503"):
        await client.get_payment("provider-payment-1")
    assert captured["url"].endswith("/payments/provider-payment-1")

    with pytest.raises(YooKassaError, match="credentials"):
        await YooKassaClient(Settings()).get_payment("provider-payment-1")
