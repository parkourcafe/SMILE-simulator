"""Mock-mode paths (v1.1): MockProvider, provider selection, mock auth stub.

These guard the North Star — a fresh clone runs the whole product with zero
credentials. If any of these break, the default `.env` no longer boots the app.
"""

from __future__ import annotations

import io

import pytest
from PIL import Image

from app.config import Settings
from app.deps import MOCK_BEARER_TOKEN, MOCK_USER, get_current_user
from app.ml.providers.mock import MockProvider
from app.ml.providers.registry import get_provider


def _png(size=(256, 256), color=(200, 170, 150)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def _mask(size=(256, 256)) -> bytes:
    img = Image.new("L", size, 0)
    for x in range(90, 170):
        for y in range(150, 190):
            img.putpixel((x, y), 255)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.mark.asyncio
async def test_mock_provider_returns_valid_png_no_cost():
    from app.ml.providers.base import ProviderConfig

    result = await MockProvider().generate(
        image=_png(), mask=_mask(), prompt="whiter teeth", config=ProviderConfig()
    )
    assert result.provider == "mock"
    assert result.cost_usd == 0.0
    assert result.duration_ms > 0
    Image.open(io.BytesIO(result.image)).verify()


@pytest.mark.asyncio
async def test_mock_provider_is_deterministic():
    from app.ml.providers.base import ProviderConfig

    img, msk = _png(), _mask()
    a = await MockProvider().generate(image=img, mask=msk, prompt="p", config=ProviderConfig())
    b = await MockProvider().generate(image=img, mask=msk, prompt="p", config=ProviderConfig())
    assert a.image == b.image


def test_registry_defaults_to_mock_when_flag_on():
    # Default Settings have mock_inference=True -> provider selection must be MockProvider.
    provider = get_provider()
    assert isinstance(provider, MockProvider)


def test_registry_explicit_name_overrides_mock():
    from app.ml.providers.fal import FalFluxFillProvider

    assert isinstance(get_provider("fal_flux_pro_fill"), FalFluxFillProvider)


@pytest.mark.asyncio
async def test_mock_auth_accepts_stub_token():
    settings = Settings(mock_auth=True)
    user = await get_current_user(authorization=f"Bearer {MOCK_BEARER_TOKEN}", settings=settings)
    assert user.id == MOCK_USER.id


@pytest.mark.asyncio
async def test_mock_auth_accepts_missing_header():
    settings = Settings(mock_auth=True)
    user = await get_current_user(authorization=None, settings=settings)
    assert user.id == MOCK_USER.id
