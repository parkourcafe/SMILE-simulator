"""Shared FastAPI dependencies: auth (Supabase JWT), admin key, current user."""

from __future__ import annotations

import asyncio
import hmac
from dataclasses import dataclass
from functools import lru_cache

import httpx
import jwt
from fastapi import Depends, Header, HTTPException, status
from jwt import PyJWKClient, PyJWTError

from app.config import Settings, get_settings

ASYMMETRIC_JWT_ALGORITHMS = {"ES256", "RS256"}


@dataclass
class CurrentUser:
    id: str
    email: str | None = None
    phone: str | None = None


def _auth_unavailable(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)


def _invalid_token() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token.",
    )


@lru_cache(maxsize=8)
def _jwks_client(jwks_url: str) -> PyJWKClient:
    # Supabase's edge caches JWKS for 10 minutes. Match that window so key rotation
    # propagates without putting Auth on the hot path for every API request.
    return PyJWKClient(jwks_url, cache_jwk_set=True, lifespan=600)


def _decode_asymmetric_jwt(token: str, settings: Settings, algorithm: str) -> dict:
    issuer = settings.supabase_auth_issuer
    signing_key = _jwks_client(f"{issuer}/.well-known/jwks.json").get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=[algorithm],
        audience="authenticated",
        issuer=issuer,
        options={"require": ["exp", "sub", "iss", "aud"]},
    )


def _decode_legacy_hs256_jwt(token: str, settings: Settings) -> dict:
    if not settings.supabase_jwt_secret:
        raise _auth_unavailable("Legacy JWT verification is not configured.")
    return jwt.decode(
        token,
        settings.supabase_jwt_secret,
        algorithms=["HS256"],
        audience="authenticated",
        issuer=settings.supabase_auth_issuer,
        options={"require": ["exp", "sub", "iss", "aud"]},
    )


async def _verify_supabase_token(token: str, settings: Settings) -> CurrentUser:
    if not settings.supabase_url:
        raise _auth_unavailable("Auth is not configured.")

    try:
        algorithm = jwt.get_unverified_header(token).get("alg")
        if algorithm in ASYMMETRIC_JWT_ALGORITHMS:
            claims = await asyncio.to_thread(
                _decode_asymmetric_jwt,
                token,
                settings,
                algorithm,
            )
        elif algorithm == "HS256":
            claims = _decode_legacy_hs256_jwt(token, settings)
        else:
            raise _invalid_token()
    except HTTPException:
        raise
    except (PyJWTError, httpx.HTTPError, OSError, ValueError) as exc:
        raise _invalid_token() from exc

    if claims.get("role") != "authenticated":
        raise _invalid_token()
    user_id = claims.get("sub")
    if not user_id:
        raise _invalid_token()
    return CurrentUser(
        id=user_id,
        email=claims.get("email"),
        phone=claims.get("phone"),
    )


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
    """Resolve a caller from a Supabase access token or the explicit dev stub."""
    if settings.mock_auth and not authorization:
        return MOCK_USER

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token.",
        )
    token = authorization.split(" ", 1)[1].strip()
    if settings.mock_auth and hmac.compare_digest(token, MOCK_BEARER_TOKEN):
        return MOCK_USER
    return await _verify_supabase_token(token, settings)


async def require_admin(
    x_admin_key: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    """Guard admin endpoints with a server-side API key."""
    if not x_admin_key or not hmac.compare_digest(x_admin_key, settings.admin_api_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin key required.",
        )
