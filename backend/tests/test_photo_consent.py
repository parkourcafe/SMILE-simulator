from __future__ import annotations

from uuid import UUID

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.deps import CurrentUser
from app.routers import generate, photo_consents
from app.schemas import GenerateRequest, PhotoConsentRequest

USER_ID = "00000000-0000-0000-0000-000000000001"
CONSENT_ID = "10000000-0000-0000-0000-000000000001"
PHOTO_PATH = f"{USER_ID}/{CONSENT_ID}_original"


class ConsentSupabase:
    def __init__(self, consent: dict | None = None):
        self.consent = consent
        self.inserted: dict | None = None

    async def insert(self, table, row):
        assert table == "photo_processing_consents"
        self.inserted = row
        return row

    async def select(self, table, *, filters=None, limit=None):
        assert table == "photo_processing_consents"
        return [self.consent] if self.consent else []


def _request(**overrides) -> PhotoConsentRequest:
    values = {
        "consent_given": True,
        "consent_version": photo_consents.PHOTO_CONSENT_VERSION,
        "consent_locale": "ru",
    }
    values.update(overrides)
    return PhotoConsentRequest(**values)


@pytest.mark.asyncio
async def test_consent_receipt_is_server_issued_before_upload(monkeypatch):
    sb = ConsentSupabase()
    monkeypatch.setattr(photo_consents, "get_supabase", lambda: sb)

    result = await photo_consents.create_photo_consent(
        _request(),
        CurrentUser(id=USER_ID),
    )

    assert isinstance(result.id, UUID)
    assert result.upload_path == f"{USER_ID}/{result.id}_original"
    assert sb.inserted == {
        "id": str(result.id),
        "user_id": USER_ID,
        "consent_given": True,
        "consent_version": photo_consents.PHOTO_CONSENT_VERSION,
        "consent_locale": "ru",
        "consent_scope": "smile_visualization",
        "photo_object_path": result.upload_path,
        "consented_at": result.consented_at.isoformat(),
    }


@pytest.mark.asyncio
async def test_generation_consent_must_belong_to_user_and_match_path():
    consent = {
        "id": CONSENT_ID,
        "user_id": USER_ID,
        "consent_given": True,
        "consent_version": photo_consents.PHOTO_CONSENT_VERSION,
        "consent_scope": "smile_visualization",
        "photo_object_path": PHOTO_PATH,
    }
    sb = ConsentSupabase(consent)

    result = await generate._validate_photo_consent(
        sb,
        consent_id=CONSENT_ID,
        user_id=USER_ID,
        photo_path=PHOTO_PATH,
    )
    assert result == consent

    with pytest.raises(HTTPException) as mismatch:
        await generate._validate_photo_consent(
            sb,
            consent_id=CONSENT_ID,
            user_id=USER_ID,
            photo_path=f"{USER_ID}/different.png",
        )
    assert mismatch.value.detail == "photo_path_consent_mismatch"

    with pytest.raises(HTTPException) as wrong_user:
        await generate._validate_photo_consent(
            sb,
            consent_id=CONSENT_ID,
            user_id="00000000-0000-0000-0000-000000000009",
            photo_path=PHOTO_PATH,
        )
    assert wrong_user.value.detail == "invalid_photo_consent"

    sb.consent = {**consent, "consent_version": "stale-version"}
    with pytest.raises(HTTPException) as stale:
        await generate._validate_photo_consent(
            sb,
            consent_id=CONSENT_ID,
            user_id=USER_ID,
            photo_path=PHOTO_PATH,
        )
    assert stale.value.detail == "stale_photo_consent"


@pytest.mark.asyncio
async def test_explicit_current_consent_and_receipt_are_required():
    with pytest.raises(ValidationError):
        _request(consent_given=False)
    with pytest.raises(ValidationError):
        _request(consent_given=1)

    with pytest.raises(HTTPException) as stale:
        await photo_consents.create_photo_consent(
            _request(consent_version="stale-version"),
            CurrentUser(id=USER_ID),
        )
    assert stale.value.detail == "unsupported_consent_version"

    with pytest.raises(ValidationError):
        GenerateRequest(
            style_id="20000000-0000-0000-0000-000000000001",
            original_photo_path=PHOTO_PATH,
        )
