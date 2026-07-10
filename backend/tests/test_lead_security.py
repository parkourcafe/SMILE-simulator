from __future__ import annotations

from uuid import UUID

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.deps import CurrentUser
from app.routers import admin, leads
from app.schemas import LeadRequest
from app.services.notifications import NotifyResult

USER_ID = "00000000-0000-0000-0000-000000000001"
CLINIC_ID = "10000000-0000-0000-0000-000000000001"
OTHER_CLINIC_ID = "10000000-0000-0000-0000-000000000002"
GENERATION_ID = "20000000-0000-0000-0000-000000000001"
LEAD_ID = "30000000-0000-0000-0000-000000000001"
IDEMPOTENCY_KEY = UUID("40000000-0000-0000-0000-000000000001")


def _request(**overrides) -> LeadRequest:
    values = {
        "clinic_id": CLINIC_ID,
        "generation_id": GENERATION_ID,
        "name": "Анна",
        "phone": "+79991234567",
        "preferred_time": "morning",
        "consent_given": True,
        "consent_version": "lead-beta-2026-07-10",
        "consent_locale": "ru",
    }
    values.update(overrides)
    return LeadRequest(**values)


class LeadSupabase:
    def __init__(self, *, existing_by_key=None, existing_by_generation=None, ready=True):
        self.existing_by_key = existing_by_key
        self.existing_by_generation = existing_by_generation
        self.ready = ready
        self.inserted: dict | None = None
        self.updates: list[tuple[str, dict]] = []

    async def select(self, table, *, filters=None, limit=None):
        if table == "leads":
            if "idempotency_key" in filters:
                return [self.existing_by_key] if self.existing_by_key else []
            return [self.existing_by_generation] if self.existing_by_generation else []
        if table == "clinics":
            return [
                {
                    "id": CLINIC_ID,
                    "name": "Clinic",
                    "status": "active",
                    "lead_price_rub": 900,
                    "phone": "+79990000000",
                    "email": "clinic@example.com",
                }
            ]
        if table == "generations":
            return [
                {
                    "id": GENERATION_ID,
                    "user_id": USER_ID,
                    "status": "completed" if self.ready else "processing",
                    "original_photo_url": f"{USER_ID}/original.jpg",
                    "result_photo_url": f"{USER_ID}/{GENERATION_ID}_result.png"
                    if self.ready
                    else None,
                }
            ]
        raise AssertionError(table)

    async def insert(self, table, row):
        assert table == "leads"
        self.inserted = row
        return {
            **row,
            "id": LEAD_ID,
            "created_at": "2026-07-10T00:00:00+00:00",
        }

    async def update(self, table, *, filters, patch):
        self.updates.append((table, patch))
        return [patch]

    async def create_signed_url(self, path, *, expires_in):
        assert expires_in == 3600
        return f"https://signed.example/{path}"


@pytest.mark.asyncio
async def test_new_lead_records_consent_and_notifies_once(monkeypatch):
    sb = LeadSupabase()
    notices = []

    async def notify(clinic, lead, result_url):
        notices.append((clinic, lead, result_url))
        return NotifyResult("email", True)

    async def deliver(**_kwargs):
        return None

    monkeypatch.setattr(leads, "get_supabase", lambda: sb)
    monkeypatch.setattr(leads, "notify_clinic", notify)
    monkeypatch.setattr(leads, "deliver_branded_result", deliver)

    result = await leads.submit_lead(
        _request(),
        IDEMPOTENCY_KEY,
        CurrentUser(id=USER_ID, email="patient@example.com"),
    )

    assert result.id == UUID(LEAD_ID)
    assert result.status == "notified"
    assert sb.inserted["idempotency_key"] == str(IDEMPOTENCY_KEY)
    assert sb.inserted["transfer_consent_given"] is True
    assert sb.inserted["transfer_consent_version"] == "lead-beta-2026-07-10"
    assert sb.inserted["transfer_consent_locale"] == "ru"
    assert sb.inserted["transfer_consented_at"].endswith("+00:00")
    assert len(notices) == 1
    assert sb.updates[0][1]["clinic_notified_at"].endswith("+00:00")


@pytest.mark.asyncio
async def test_idempotent_retry_returns_existing_without_second_notification(monkeypatch):
    existing = {
        "id": LEAD_ID,
        "user_id": USER_ID,
        "clinic_id": CLINIC_ID,
        "generation_id": GENERATION_ID,
        "status": "notified",
        "created_at": "2026-07-10T00:00:00+00:00",
    }
    sb = LeadSupabase(existing_by_key=existing)

    async def should_not_notify(*_args, **_kwargs):
        raise AssertionError("duplicate notification")

    monkeypatch.setattr(leads, "get_supabase", lambda: sb)
    monkeypatch.setattr(leads, "notify_clinic", should_not_notify)

    result = await leads.submit_lead(
        _request(),
        IDEMPOTENCY_KEY,
        CurrentUser(id=USER_ID),
    )
    assert result.id == UUID(LEAD_ID)
    assert sb.inserted is None


@pytest.mark.asyncio
async def test_generation_cannot_be_shared_with_second_clinic(monkeypatch):
    existing = {
        "id": LEAD_ID,
        "user_id": USER_ID,
        "clinic_id": OTHER_CLINIC_ID,
        "generation_id": GENERATION_ID,
        "status": "new",
    }
    sb = LeadSupabase(existing_by_generation=existing)
    monkeypatch.setattr(leads, "get_supabase", lambda: sb)

    with pytest.raises(HTTPException) as exc:
        await leads.submit_lead(
            _request(),
            IDEMPOTENCY_KEY,
            CurrentUser(id=USER_ID),
        )
    assert exc.value.status_code == 409
    assert exc.value.detail == "generation_already_shared"


@pytest.mark.asyncio
async def test_lead_requires_completed_generation(monkeypatch):
    sb = LeadSupabase(ready=False)
    monkeypatch.setattr(leads, "get_supabase", lambda: sb)
    with pytest.raises(HTTPException) as exc:
        await leads.submit_lead(
            _request(),
            IDEMPOTENCY_KEY,
            CurrentUser(id=USER_ID),
        )
    assert exc.value.status_code == 409
    assert exc.value.detail == "generation_not_ready"


def test_lead_requires_explicit_transfer_consent_and_e164_phone():
    with pytest.raises(ValidationError):
        _request(consent_given=False)
    with pytest.raises(ValidationError):
        _request(consent_given=1)
    with pytest.raises(ValidationError):
        _request(phone="89991234567")


class ClinicKeySupabase:
    def __init__(self, plaintext: str):
        self.plaintext = plaintext
        self.updated = False

    async def select(self, table, *, filters=None, limit=None):
        if table == "clinic_api_keys":
            expected = f"eq.{leads.hash_clinic_api_key(self.plaintext)}"
            if filters["key_hash"] != expected:
                return []
            return [{"id": "key-1", "clinic_id": CLINIC_ID, "status": "active"}]
        if table == "clinics":
            return [{"id": CLINIC_ID, "name": "Clinic", "status": "active"}]
        raise AssertionError(table)

    async def update(self, table, *, filters, patch):
        assert table == "clinic_api_keys"
        self.updated = True
        return [patch]


@pytest.mark.asyncio
async def test_clinic_dashboard_uses_hashed_revocable_key_not_clinic_id():
    plaintext = "zlk_abcdefghijklmnopqrstuvwxyz1234567890"
    sb = ClinicKeySupabase(plaintext)
    clinic = await leads._clinic_from_key(sb, plaintext)
    assert clinic["id"] == CLINIC_ID
    assert sb.updated is True

    with pytest.raises(HTTPException) as exc:
        await leads._clinic_from_key(sb, CLINIC_ID)
    assert exc.value.status_code == 403


class AdminKeySupabase:
    def __init__(self):
        self.inserted = None

    async def select(self, table, *, filters=None, limit=None):
        assert table == "clinics"
        return [{"id": CLINIC_ID}]

    async def insert(self, table, row):
        assert table == "clinic_api_keys"
        self.inserted = row
        return {"id": "key-1", **row}


@pytest.mark.asyncio
async def test_admin_returns_clinic_key_once_and_stores_only_hash(monkeypatch):
    sb = AdminKeySupabase()
    monkeypatch.setattr(admin, "get_supabase", lambda: sb)
    monkeypatch.setattr(admin.secrets, "token_urlsafe", lambda _size: "fixed-secret-material")

    result = await admin.create_clinic_key(CLINIC_ID, label="pilot")
    assert result["key"] == "zlk_fixed-secret-material"
    assert sb.inserted["key_hash"] == leads.hash_clinic_api_key(result["key"])
    assert sb.inserted["key_hash"] != result["key"]
