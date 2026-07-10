"""Bounded retries for idempotent external HTTP reads only."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

TRANSIENT_GET_STATUSES = {408, 425, 429, 500, 502, 503, 504}


async def get_with_retry(
    client: Any,
    url: str,
    *,
    attempts: int = 3,
    backoff_seconds: float = 0.2,
    **kwargs: Any,
) -> Any:
    """GET with bounded exponential backoff for transport and transient HTTP failures."""
    if not 1 <= attempts <= 5:
        raise ValueError("attempts must be between 1 and 5")
    if backoff_seconds < 0:
        raise ValueError("backoff_seconds cannot be negative")

    for attempt in range(attempts):
        try:
            response = await client.get(url, **kwargs)
        except httpx.TransportError:
            if attempt + 1 >= attempts:
                raise
        else:
            if response.status_code not in TRANSIENT_GET_STATUSES or attempt + 1 >= attempts:
                return response
        await asyncio.sleep(backoff_seconds * (2**attempt))

    raise RuntimeError("unreachable")
