"""AI Smile Simulator — API gateway entrypoint.

The gateway orchestrates the ML pipeline, enforces generation limits, protects the
inference API key, and logs cost. The inference provider is NEVER reachable from the
mobile client (architecture §1.1, CLAUDE.md critical rule).
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.config import get_settings
from app.observability import configure_logging, configure_sentry, install_observability
from app.routers import (
    admin,
    clinics,
    generate,
    leads,
    packs,
    photo_consents,
    price_estimates,
    styles,
    webhooks,
)
from app.services.supabase_client import SupabaseError, get_supabase

settings = get_settings()
settings.assert_safe_startup()
configure_logging()
configure_sentry(settings, release=f"zubilook-api@{__version__}")

app = FastAPI(
    title="AI Smile Simulator API",
    version=__version__,
    description="Inference orchestration, auth, limits, payments, and B2B leads.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Idempotency-Key",
        "X-Admin-Key",
        "X-Clinic-Key",
    ],
    expose_headers=["X-Request-ID"],
)
install_observability(app)

app.include_router(generate.router, prefix="/v1")
app.include_router(styles.router, prefix="/v1")
app.include_router(packs.router, prefix="/v1")
app.include_router(clinics.router, prefix="/v1")
app.include_router(price_estimates.router, prefix="/v1")
app.include_router(leads.router, prefix="/v1")
app.include_router(photo_consents.router, prefix="/v1")
app.include_router(admin.router, prefix="/v1")
app.include_router(webhooks.router, prefix="/v1")


@app.get("/health", tags=["meta"])
async def health() -> dict:
    effective_provider = (
        "mock"
        if (settings.mock_inference or not settings.fal_api_key)
        else settings.inference_provider
    )
    return {
        "status": "ok",
        "version": __version__,
        "env": settings.app_env,
        "supabase_configured": settings.supabase_configured,
        "inference_provider": effective_provider,
        "mocks": {
            "inference": settings.mock_inference,
            "auth": settings.mock_auth,
            "payments": settings.mock_payments,
        },
    }


@app.get("/ready", tags=["meta"])
async def readiness() -> JSONResponse:
    """Dependency-aware deployment gate; liveness remains available at /health."""
    checks = {
        "supabase": "unavailable",
        "face_model": "not_required" if settings.mock_inference else "unavailable",
    }

    try:
        await get_supabase().ping()
        checks["supabase"] = "ok"
    except SupabaseError:
        pass

    if not settings.mock_inference and settings.face_model_is_valid():
        checks["face_model"] = "ok"

    ready = all(value in {"ok", "not_required"} for value in checks.values())
    return JSONResponse(
        status_code=200 if ready else 503,
        content={"status": "ready" if ready else "not_ready", "checks": checks},
    )
