"""Authenticated consent receipts issued before any selfie upload."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from app.deps import CurrentUser, get_current_user
from app.schemas import PhotoConsentOut, PhotoConsentRequest
from app.services.supabase_client import get_supabase

PHOTO_CONSENT_VERSION = "photo-beta-2026-07-10"

router = APIRouter(prefix="/api/photo-consents", tags=["privacy"])


@router.post("", response_model=PhotoConsentOut, status_code=status.HTTP_201_CREATED)
async def create_photo_consent(
    body: PhotoConsentRequest,
    user: CurrentUser = Depends(get_current_user),
) -> PhotoConsentOut:
    if body.consent_version != PHOTO_CONSENT_VERSION:
        raise HTTPException(status_code=422, detail="unsupported_consent_version")

    consent_id = uuid4()
    consented_at = datetime.now(UTC)
    upload_path = f"{user.id}/{consent_id}_original"
    row = await get_supabase().insert(
        "photo_processing_consents",
        {
            "id": str(consent_id),
            "user_id": user.id,
            "consent_given": True,
            "consent_version": body.consent_version,
            "consent_locale": body.consent_locale,
            "consent_scope": "smile_visualization",
            "photo_object_path": upload_path,
            "consented_at": consented_at.isoformat(),
        },
    )
    return PhotoConsentOut(
        id=row["id"],
        consent_version=row["consent_version"],
        consent_locale=row["consent_locale"],
        consented_at=row["consented_at"],
        upload_path=row["photo_object_path"],
    )
