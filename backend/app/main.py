"""AI Smile Simulator — API gateway entrypoint.

The gateway orchestrates the ML pipeline, enforces generation limits, protects the
inference API key, and logs cost. The inference provider is NEVER reachable from the
mobile client (architecture §1.1, CLAUDE.md critical rule).
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.config import get_settings
from app.routers import admin, clinics, generate, leads, packs, styles, webhooks

logging.basicConfig(level=logging.INFO)

settings = get_settings()

app = FastAPI(
    title="AI Smile Simulator API",
    version=__version__,
    description="Inference orchestration, auth, limits, payments, and B2B leads.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO(phase-1): restrict to app + clinic web origins.
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(generate.router, prefix="/v1")
app.include_router(styles.router, prefix="/v1")
app.include_router(packs.router, prefix="/v1")
app.include_router(clinics.router, prefix="/v1")
app.include_router(leads.router, prefix="/v1")
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
        "supabase_configured": bool(settings.supabase_url and settings.supabase_service_role_key),
        "inference_provider": effective_provider,
        "mocks": {
            "inference": settings.mock_inference,
            "auth": settings.mock_auth,
            "payments": settings.mock_payments,
        },
    }
