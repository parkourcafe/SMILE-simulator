"""Minimal YooKassa HTTP Basic Auth client for redirect payments."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import httpx

from app.config import Settings, get_settings

YOOKASSA_API_BASE = "https://api.yookassa.ru/v3"


class YooKassaError(RuntimeError):
    pass


class YooKassaClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def _auth(self) -> httpx.BasicAuth:
        if not self.settings.yookassa_shop_id or not self.settings.yookassa_secret_key:
            raise YooKassaError("YooKassa credentials are not configured")
        return httpx.BasicAuth(
            username=self.settings.yookassa_shop_id,
            password=self.settings.yookassa_secret_key,
        )

    @staticmethod
    def _validate_payment(payload: Any) -> dict[str, Any]:
        if not isinstance(payload, dict) or not isinstance(payload.get("id"), str):
            raise YooKassaError("YooKassa returned an invalid payment object")
        if payload.get("status") not in {
            "pending",
            "waiting_for_capture",
            "succeeded",
            "canceled",
        }:
            raise YooKassaError("YooKassa returned an unknown payment status")
        amount = payload.get("amount")
        if not isinstance(amount, dict) or "value" not in amount or "currency" not in amount:
            raise YooKassaError("YooKassa payment amount is missing")
        return payload

    async def create_payment(
        self,
        *,
        idempotency_key: str,
        amount: Decimal,
        currency: str,
        description: str,
        metadata: dict[str, str],
    ) -> dict[str, Any]:
        if not self.settings.yookassa_return_url.startswith("https://"):
            raise YooKassaError("YooKassa return URL is not configured")
        payload = {
            "amount": {"value": f"{amount:.2f}", "currency": currency},
            "capture": True,
            "confirmation": {
                "type": "redirect",
                "return_url": self.settings.yookassa_return_url,
            },
            "description": description[:128],
            "metadata": metadata,
        }
        try:
            async with httpx.AsyncClient(auth=self._auth(), timeout=30) as client:
                response = await client.post(
                    f"{YOOKASSA_API_BASE}/payments",
                    headers={"Idempotence-Key": idempotency_key},
                    json=payload,
                )
        except httpx.HTTPError as exc:
            raise YooKassaError("YooKassa create payment request failed") from exc
        if response.status_code >= 400:
            raise YooKassaError(f"YooKassa create payment failed: {response.status_code}")
        try:
            response_payload = response.json()
        except ValueError as exc:
            raise YooKassaError("YooKassa returned invalid JSON") from exc
        return self._validate_payment(response_payload)

    async def get_payment(self, provider_payment_id: str) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(auth=self._auth(), timeout=15) as client:
                response = await client.get(f"{YOOKASSA_API_BASE}/payments/{provider_payment_id}")
        except httpx.HTTPError as exc:
            raise YooKassaError("YooKassa get payment request failed") from exc
        if response.status_code >= 400:
            raise YooKassaError(f"YooKassa get payment failed: {response.status_code}")
        try:
            response_payload = response.json()
        except ValueError as exc:
            raise YooKassaError("YooKassa returned invalid JSON") from exc
        return self._validate_payment(response_payload)


def get_yookassa_client() -> YooKassaClient:
    return YooKassaClient()
