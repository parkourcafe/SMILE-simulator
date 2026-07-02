"""Shared FastAPI dependencies: auth (Supabase JWT), admin key, current user."""

from __future__ import annotations

from dataclasses import dataclass

import jwt
from fastapi import Depends, Header, HTTPException, status
from jwt import PyJWTError

from app.config import Settings, get_settings


@dataclass
class CurrentUser:
    id: str
    email: str | None = None
    phone: str | None = None


def _decode_supabase_jwt(token: str, settings: Settings) -> dict:
    """Verify a Supabase access token (HS256, signed with the project JWT secret)."""
    if not settings.supabase_jwt_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth not configured (SUPABASE_JWT_SECRET missing).",
        )
    try:
        return jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except PyJWTError as exc:  # invalid signature / expired / wrong audience
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token."
        ) from exc


# Deterministic dev user when MOCK_AUTH is on and the caller sends the stub token.
MOCK_BEARER_TOKEN = "mock-dev-token"  # noqa: S105 - not a secret; dev-only stub
MOCK_USER = CurrentUser(
    id="00000000-0000-0000-0000-000000000001",
    email="dev@smilesim.app",
    phone="+70000000000",
)


async def get_current_user(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> CurrentUser:
    """Resolve the caller from the ``Authorization: Bearer <supabase_jwt>`` header.

    With ``MOCK_AUTH=true`` (default), a bearer value of ``mock-dev-token`` — or an
    empty/absent header — resolves to a fixed dev user, so the app is clickable end
    to end before Supabase Auth exists. Real Supabase JWTs are still verified if sent.
    """
    if settings.mock_auth:
        if authorization and authorization.lower().startswith("bearer "):
            token = authorization.split(" ", 1)[1].strip()
            if token and token != MOCK_BEARER_TOKEN:
                # A real-looking token was sent — verify it rather than silently stub.
                claims = _decode_supabase_jwt(token, settings)
                return CurrentUser(
                    id=claims.get("sub", MOCK_USER.id),
                    email=claims.get("email"),
                    phone=claims.get("phone"),
                )
        return MOCK_USER

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token."
        )
    token = authorization.split(" ", 1)[1].strip()
    claims = _decode_supabase_jwt(token, settings)
    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing sub.")
    return CurrentUser(
        id=user_id,
        email=claims.get("email"),
        phone=claims.get("phone"),
    )


async def require_admin(
    x_admin_key: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    """Guard admin endpoints with a static admin API key (architecture §4.6)."""
    if not x_admin_key or x_admin_key != settings.admin_api_key:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin key required.")
