from __future__ import annotations

import httpx
import pytest

from app.services.http_retry import get_with_retry


class Response:
    def __init__(self, status_code: int):
        self.status_code = status_code


class SequenceClient:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0

    async def get(self, _url, **_kwargs):
        outcome = self.outcomes[self.calls]
        self.calls += 1
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


async def test_get_retries_transient_status_and_returns_success():
    client = SequenceClient([Response(503), Response(429), Response(200)])

    response = await get_with_retry(
        client,
        "https://api.example.test/resource",
        attempts=3,
        backoff_seconds=0,
    )

    assert response.status_code == 200
    assert client.calls == 3


async def test_get_does_not_retry_non_transient_status():
    client = SequenceClient([Response(404), Response(200)])

    response = await get_with_retry(
        client,
        "https://api.example.test/resource",
        attempts=3,
        backoff_seconds=0,
    )

    assert response.status_code == 404
    assert client.calls == 1


async def test_get_network_retries_are_bounded():
    request = httpx.Request("GET", "https://api.example.test/resource")
    client = SequenceClient(
        [
            httpx.ConnectError("unavailable", request=request),
            httpx.ConnectError("unavailable", request=request),
            httpx.ConnectError("unavailable", request=request),
        ]
    )

    with pytest.raises(httpx.ConnectError):
        await get_with_retry(
            client,
            "https://api.example.test/resource",
            attempts=3,
            backoff_seconds=0,
        )

    assert client.calls == 3
