from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import HTTPException

from app import deps
from app.config import Settings
from app.deps import get_current_user


def _legacy_token(secret: str, *, role: str = "authenticated") -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": "8c3a3548-d901-4d78-9f11-4fac970c5ab7",
            "email": "beta@example.com",
            "role": role,
            "aud": "authenticated",
            "iss": "https://project.supabase.co/auth/v1",
            "iat": now,
            "exp": now + timedelta(minutes=10),
        },
        secret,
        algorithm="HS256",
    )


@pytest.mark.asyncio
async def test_legacy_hs256_token_is_verified_during_key_migration():
    secret = "legacy-jwt-secret-for-tests-at-least-32-bytes"
    settings = Settings(
        mock_auth=False,
        supabase_url="https://project.supabase.co",
        supabase_jwt_secret=secret,
    )
    user = await get_current_user(
        authorization=f"Bearer {_legacy_token(secret)}",
        settings=settings,
    )
    assert user.id == "8c3a3548-d901-4d78-9f11-4fac970c5ab7"
    assert user.email == "beta@example.com"


@pytest.mark.asyncio
async def test_es256_token_is_verified_with_project_jwks(monkeypatch):
    private_key = ec.generate_private_key(ec.SECP256R1())
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": "28b094c2-feb7-4ed1-a8d7-2990884c6476",
            "phone": "+998901234567",
            "role": "authenticated",
            "aud": "authenticated",
            "iss": "https://project.supabase.co/auth/v1",
            "iat": now,
            "exp": now + timedelta(minutes=10),
        },
        private_key,
        algorithm="ES256",
        headers={"kid": "test-key"},
    )

    client = SimpleNamespace(
        get_signing_key_from_jwt=lambda _token: SimpleNamespace(key=private_key.public_key())
    )
    monkeypatch.setattr(deps, "_jwks_client", lambda _url: client)

    user = await get_current_user(
        authorization=f"Bearer {token}",
        settings=Settings(mock_auth=False, supabase_url="https://project.supabase.co"),
    )
    assert user.id == "28b094c2-feb7-4ed1-a8d7-2990884c6476"
    assert user.phone == "+998901234567"


@pytest.mark.asyncio
async def test_token_role_must_be_authenticated():
    secret = "legacy-jwt-secret-for-tests-at-least-32-bytes"
    settings = Settings(
        mock_auth=False,
        supabase_url="https://project.supabase.co",
        supabase_jwt_secret=secret,
    )
    with pytest.raises(HTTPException) as exc:
        await get_current_user(
            authorization=f"Bearer {_legacy_token(secret, role='service_role')}",
            settings=settings,
        )
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_mock_auth_does_not_accept_an_arbitrary_bearer_token():
    with pytest.raises(HTTPException) as exc:
        await get_current_user(
            authorization="Bearer not-a-jwt",
            settings=Settings(mock_auth=True, supabase_url="https://project.supabase.co"),
        )
    assert exc.value.status_code == 401


def _otherwise_safe_production_settings(model_path: Path, **overrides) -> Settings:
    model_path.write_bytes(b"verified-face-landmarker")
    values = {
        "app_env": "production",
        "mock_auth": False,
        "mock_inference": False,
        "mock_payments": False,
        "supabase_url": "https://project.supabase.co",
        "supabase_publishable_key": "sb_publishable_test",
        "supabase_secret_key": "sb_secret_test",
        "fal_api_key": "fal_test",
        "mediapipe_face_model": str(model_path),
        "mediapipe_face_model_sha256": hashlib.sha256(model_path.read_bytes()).hexdigest(),
        "yookassa_shop_id": "shop_test",
        "yookassa_secret_key": "payment_test",
        "yookassa_return_url": "https://www.zubilook.com/?payment=return",
        "smtp_host": "smtp.example.test",
        "sentry_dsn": "https://public@sentry.example.test/1",
        "admin_api_key": "a" * 32,
        "cors_allowed_origins": "https://www.zubilook.com",
    }
    values.update(overrides)
    return Settings(**values)


def test_safe_production_configuration_passes_startup_guard(tmp_path):
    _otherwise_safe_production_settings(tmp_path / "model.task").assert_safe_startup()


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"mock_auth": True}, "MOCK_AUTH"),
        ({"mock_inference": True}, "MOCK_INFERENCE"),
        ({"mock_payments": True}, "MOCK_PAYMENTS"),
        ({"admin_api_key": "change-me"}, "ADMIN_API_KEY"),
        ({"cors_allowed_origins": "*"}, "CORS_ALLOWED_ORIGINS"),
        ({"cors_allowed_origins": "http://localhost:3000"}, "local origins"),
        ({"supabase_secret_key": ""}, "SUPABASE_SECRET_KEY"),
        ({"fal_api_key": ""}, "FAL_API_KEY"),
        ({"mediapipe_face_model_sha256": "wrong"}, "MEDIAPIPE_FACE_MODEL"),
        ({"yookassa_secret_key": ""}, "YooKassa"),
        ({"yookassa_return_url": "http://localhost/payment"}, "YOOKASSA_RETURN_URL"),
        ({"smtp_host": ""}, "SMTP or WhatsApp"),
        ({"sentry_dsn": ""}, "SENTRY_DSN"),
        ({"photo_retention_days": 31}, "PHOTO_RETENTION_DAYS"),
        (
            {"generation_reservation_timeout_minutes": 2},
            "GENERATION_RESERVATION_TIMEOUT_MINUTES",
        ),
        ({"rate_limit_per_minute": 0}, "RATE_LIMIT_PER_MINUTE"),
    ],
)
def test_unsafe_production_configuration_is_rejected(tmp_path, overrides, message):
    with pytest.raises(RuntimeError, match=message):
        _otherwise_safe_production_settings(
            tmp_path / "model.task", **overrides
        ).assert_safe_startup()
