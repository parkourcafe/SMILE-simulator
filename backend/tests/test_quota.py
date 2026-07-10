from __future__ import annotations

from uuid import UUID

import pytest
from fastapi import BackgroundTasks, HTTPException

from app.deps import CurrentUser
from app.routers import generate
from app.schemas import GenerateRequest
from app.services import quota
from app.services.supabase_client import SupabaseError

USER_ID = "00000000-0000-0000-0000-000000000001"
STYLE_ID = "10000000-0000-0000-0000-000000000001"
CONSENT_ID = "20000000-0000-0000-0000-000000000001"
GENERATION_ID = "30000000-0000-0000-0000-000000000001"
PHOTO_PATH = f"{USER_ID}/{CONSENT_ID}_original"


class RpcSupabase:
    def __init__(self, result):
        self.result = result
        self.call = None

    async def rpc(self, function, params):
        self.call = (function, params)
        return self.result


@pytest.mark.asyncio
async def test_reservation_uses_single_database_rpc():
    generation = {
        "id": GENERATION_ID,
        "status": "pending",
        "has_watermark": True,
        "quota_source": "free",
        "quota_state": "reserved",
    }
    sb = RpcSupabase({"allowed": True, "generation": generation})

    result = await quota.reserve_generation(
        sb,
        user_id=USER_ID,
        style_id=STYLE_ID,
        photo_consent_id=CONSENT_ID,
        original_photo_path=PHOTO_PATH,
    )

    assert result.allowed is True
    assert result.generation == generation
    assert sb.call == (
        "reserve_generation_quota",
        {
            "p_user_id": USER_ID,
            "p_style_id": STYLE_ID,
            "p_photo_consent_id": CONSENT_ID,
            "p_original_photo_path": PHOTO_PATH,
            "p_rate_limit": 5,
        },
    )


@pytest.mark.asyncio
async def test_reservation_denial_and_malformed_result_fail_closed():
    denied = await quota.reserve_generation(
        RpcSupabase({"allowed": False, "reason": "limit_reached"}),
        user_id=USER_ID,
        style_id=STYLE_ID,
        photo_consent_id=CONSENT_ID,
        original_photo_path=PHOTO_PATH,
    )
    assert denied.allowed is False
    assert denied.reason == "limit_reached"

    with pytest.raises(SupabaseError, match="invalid response"):
        await quota.reserve_generation(
            RpcSupabase({"allowed": "yes"}),
            user_id=USER_ID,
            style_id=STYLE_ID,
            photo_consent_id=CONSENT_ID,
            original_photo_path=PHOTO_PATH,
        )


class GenerateSupabase(RpcSupabase):
    def __init__(self, result):
        super().__init__(result)
        self.insert_called = False

    async def select(self, table, *, filters=None, limit=None):
        if table == "photo_processing_consents":
            return [
                {
                    "id": CONSENT_ID,
                    "user_id": USER_ID,
                    "consent_given": True,
                    "consent_version": "photo-beta-2026-07-10",
                    "consent_scope": "smile_visualization",
                    "photo_object_path": PHOTO_PATH,
                }
            ]
        if table == "styles":
            assert filters["is_active"] == "eq.true"
            return [{"id": STYLE_ID, "name": "Natural", "prompt_template": "prompt"}]
        raise AssertionError(table)

    async def insert(self, *_args, **_kwargs):
        self.insert_called = True
        raise AssertionError("generation creation must happen inside the reservation RPC")


def _generate_request() -> GenerateRequest:
    return GenerateRequest(
        style_id=UUID(STYLE_ID),
        photo_consent_id=UUID(CONSENT_ID),
        original_photo_path=PHOTO_PATH,
    )


@pytest.mark.asyncio
async def test_start_generation_returns_402_without_scheduling_inference(monkeypatch):
    sb = GenerateSupabase({"allowed": False, "reason": "limit_reached"})
    monkeypatch.setattr(generate, "get_supabase", lambda: sb)
    background = BackgroundTasks()

    with pytest.raises(HTTPException) as exc:
        await generate.start_generation(
            _generate_request(),
            background,
            CurrentUser(id=USER_ID),
        )

    assert exc.value.status_code == 402
    assert exc.value.detail == "limit_reached"
    assert not background.tasks
    assert sb.insert_called is False


@pytest.mark.asyncio
async def test_start_generation_returns_429_with_retry_after(monkeypatch):
    sb = GenerateSupabase({"allowed": False, "reason": "rate_limited"})
    monkeypatch.setattr(generate, "get_supabase", lambda: sb)

    with pytest.raises(HTTPException) as exc:
        await generate.start_generation(
            _generate_request(),
            BackgroundTasks(),
            CurrentUser(id=USER_ID),
        )

    assert exc.value.status_code == 429
    assert exc.value.headers == {"Retry-After": "60"}


@pytest.mark.asyncio
async def test_start_generation_schedules_only_the_reserved_row(monkeypatch):
    row = {
        "id": GENERATION_ID,
        "status": "pending",
        "style_id": STYLE_ID,
        "has_watermark": True,
        "quota_source": "free",
        "quota_state": "reserved",
    }
    sb = GenerateSupabase({"allowed": True, "generation": row})
    monkeypatch.setattr(generate, "get_supabase", lambda: sb)
    background = BackgroundTasks()

    result = await generate.start_generation(
        _generate_request(),
        background,
        CurrentUser(id=USER_ID),
    )

    assert result.id == UUID(GENERATION_ID)
    assert result.has_watermark is True
    assert len(background.tasks) == 1
    assert sb.insert_called is False
