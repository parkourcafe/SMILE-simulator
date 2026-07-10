"""Generation endpoints (architecture §4.2).

Flow for POST /api/generate:
  1. Check the user has remaining generations (free or pack).
  2. Create a generation row (status=pending) and start the async pipeline.
  3. Return generation_id immediately; the client polls GET /:id until completed.

The mobile client uploads the selfie directly to private Storage (signed URL) and
passes the object path here — the photo never transits the API body (architecture
§10.3, less bandwidth + smaller attack surface).
"""

from __future__ import annotations

import logging
from pathlib import PurePosixPath

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from app.deps import CurrentUser, get_current_user
from app.ml.face_mesh import FaceDetectionError
from app.ml.photo import PhotoValidationError
from app.ml.pipeline import run_pipeline
from app.ml.providers.base import (  # noqa: F401 (documents the contract)
    InferenceProviderError,
    ProviderConfig,
)
from app.observability import capture_exception, get_request_id, request_id_context
from app.routers.photo_consents import PHOTO_CONSENT_VERSION
from app.schemas import (
    GenerateRequest,
    GenerationListOut,
    GenerationOut,
    PhotoDeletionOut,
    PhotoDeletionSummary,
    RetryRequest,
)
from app.services import quota
from app.services.retention import generation_photo_paths, purge_generation_photos
from app.services.supabase_client import SupabaseClient, SupabaseError, get_supabase

router = APIRouter(prefix="/api/generate", tags=["generation"])
log = logging.getLogger("smile.generate")

_PHOTO_ERROR_CODES = {
    "file_too_large",
    "unreadable_image",
    "unsupported_format",
    "too_small",
    "too_large_dimensions",
}


def _generation_error_code(exc: Exception) -> str:
    if isinstance(exc, PhotoValidationError) and str(exc) in _PHOTO_ERROR_CODES:
        return str(exc)
    if isinstance(exc, FaceDetectionError):
        return "multiple_faces" if str(exc) == "multiple_faces" else "no_face"
    if isinstance(exc, InferenceProviderError):
        return exc.code
    return "generation_failed"


def _validate_owned_photo_path(path: str, user_id: str) -> None:
    parts = PurePosixPath(path).parts
    if (
        not path
        or path.startswith("/")
        or "\\" in path
        or len(parts) < 2
        or parts[0] != user_id
        or any(part in {".", ".."} for part in parts)
    ):
        raise HTTPException(status_code=422, detail="invalid_photo_path")


async def _signed(sb: SupabaseClient, path: str | None) -> str | None:
    if not path:
        return None
    try:
        return await sb.create_signed_url(path)
    except SupabaseError:
        return None


async def _validate_photo_consent(
    sb: SupabaseClient,
    *,
    consent_id: str,
    user_id: str,
    photo_path: str,
) -> dict:
    rows = await sb.select(
        "photo_processing_consents",
        filters={"id": f"eq.{consent_id}"},
        limit=1,
    )
    if not rows or rows[0].get("user_id") != user_id:
        raise HTTPException(status_code=422, detail="invalid_photo_consent")
    consent = rows[0]
    if consent.get("consent_given") is not True:
        raise HTTPException(status_code=422, detail="invalid_photo_consent")
    if (
        consent.get("consent_version") != PHOTO_CONSENT_VERSION
        or consent.get("consent_scope") != "smile_visualization"
    ):
        raise HTTPException(status_code=422, detail="stale_photo_consent")
    if consent.get("photo_object_path") != photo_path:
        raise HTTPException(status_code=422, detail="photo_path_consent_mismatch")
    return consent


def _to_out(
    row: dict, original_url: str | None = None, result_url: str | None = None
) -> GenerationOut:
    return GenerationOut(
        id=row["id"],
        status=row["status"],
        style_id=row.get("style_id"),
        original_photo_url=original_url,
        result_photo_url=result_url,
        has_watermark=row.get("has_watermark", False),
        quality_score=row.get("quality_score"),
        inference_duration_ms=row.get("inference_duration_ms"),
        error_message=row.get("error_message"),
        created_at=row.get("created_at"),
    )


async def _process(
    generation_id: str,
    user_id: str,
    photo_path: str,
    style: dict,
    watermark: bool,
    originating_request_id: str | None = None,
) -> None:
    """Run inference; the database trigger settles or releases reserved quota."""
    with request_id_context(originating_request_id):
        sb = get_supabase()
        try:
            await sb.update(
                "generations", filters={"id": f"eq.{generation_id}"}, patch={"status": "processing"}
            )
            photo_bytes = await sb.download(photo_path)
            out = await run_pipeline(
                photo_bytes=photo_bytes,
                style_template=style["prompt_template"],
                style_name=style["name"],
                apply_watermark=watermark,
            )
            current = await sb.select(
                "generations",
                filters={"id": f"eq.{generation_id}"},
                limit=1,
            )
            if not current or current[0].get("deleted_at"):
                log.info("generation %s was deleted while processing", generation_id)
                return

            result_path = f"{user_id}/{generation_id}_result.png"
            mask_path = f"{user_id}/{generation_id}_mask.png"
            await sb.upload(result_path, out.result_image)
            await sb.upload(mask_path, out.mask_image)
            updated = await sb.update(
                "generations",
                filters={"id": f"eq.{generation_id}", "deleted_at": "is.null"},
                patch={
                    "status": "completed",
                    "result_photo_url": result_path,
                    "mask_url": mask_path,
                    "prompt": out.prompt,
                    "inference_provider": out.provider,
                    "inference_cost_usd": out.cost_usd,
                    "inference_duration_ms": out.duration_ms,
                    "quality_score": out.quality_score,
                },
            )
            if not updated:
                await sb.remove_objects([result_path, mask_path])
                log.info("discarded result for deleted generation %s", generation_id)
                return
        except Exception as exc:  # noqa: BLE001 - record failure, do not crash worker
            capture_exception(exc)
            log.error(
                "generation_failed",
                extra={
                    "event": "generation_failed",
                    "generation_id": generation_id,
                    "error_type": type(exc).__name__,
                },
            )
            try:
                await sb.update(
                    "generations",
                    filters={"id": f"eq.{generation_id}", "deleted_at": "is.null"},
                    patch={"status": "failed", "error_message": _generation_error_code(exc)},
                )
            except Exception as persistence_exc:  # noqa: BLE001 - watchdog releases the quota
                capture_exception(persistence_exc)
                log.error(
                    "generation_failure_persistence_failed",
                    extra={
                        "event": "generation_failure_persistence_failed",
                        "generation_id": generation_id,
                        "error_type": type(persistence_exc).__name__,
                    },
                )


@router.post("", response_model=GenerationOut, status_code=202)
async def start_generation(
    body: GenerateRequest,
    background: BackgroundTasks,
    user: CurrentUser = Depends(get_current_user),
) -> GenerationOut:
    sb = get_supabase()
    _validate_owned_photo_path(body.original_photo_path, user.id)
    await _validate_photo_consent(
        sb,
        consent_id=str(body.photo_consent_id),
        user_id=user.id,
        photo_path=body.original_photo_path,
    )
    styles = await sb.select(
        "styles",
        filters={"id": f"eq.{body.style_id}", "is_active": "eq.true"},
        limit=1,
    )
    if not styles:
        raise HTTPException(status_code=404, detail="style_not_found")
    style = styles[0]

    reservation = await quota.reserve_generation(
        sb,
        user_id=user.id,
        style_id=str(body.style_id),
        photo_consent_id=str(body.photo_consent_id),
        original_photo_path=body.original_photo_path,
    )
    if not reservation.allowed:
        reason = reservation.reason or "limit_reached"
        status_code = {
            "limit_reached": 402,
            "rate_limited": 429,
            "style_not_found": 404,
            "invalid_photo_consent": 422,
            "user_profile_not_ready": 409,
        }.get(reason, 409)
        headers = {"Retry-After": "60"} if reason == "rate_limited" else None
        raise HTTPException(status_code=status_code, detail=reason, headers=headers)
    row = reservation.generation
    if row is None:  # reserve_generation validates this; keep type narrowing explicit.
        raise RuntimeError("generation reservation did not return a row")

    background.add_task(
        _process,
        row["id"],
        user.id,
        body.original_photo_path,
        style,
        bool(row["has_watermark"]),
        get_request_id(),
    )
    return _to_out(row)


@router.get("/history", response_model=GenerationListOut)
async def history(
    limit: int = 20, user: CurrentUser = Depends(get_current_user)
) -> GenerationListOut:
    sb = get_supabase()
    rows = await sb.select(
        "generations",
        filters={
            "user_id": f"eq.{user.id}",
            "deleted_at": "is.null",
            "order": "created_at.desc",
        },
        limit=limit,
    )
    items = [
        _to_out(
            r,
            await _signed(sb, r.get("original_photo_url")),
            await _signed(sb, r.get("result_photo_url")),
        )
        for r in rows
    ]
    return GenerationListOut(items=items)


@router.get("/{generation_id}", response_model=GenerationOut)
async def get_generation(
    generation_id: str, user: CurrentUser = Depends(get_current_user)
) -> GenerationOut:
    sb = get_supabase()
    rows = await sb.select(
        "generations",
        filters={"id": f"eq.{generation_id}", "deleted_at": "is.null"},
        limit=1,
    )
    if not rows or rows[0]["user_id"] != user.id:
        raise HTTPException(status_code=404, detail="not_found")
    row = rows[0]
    return _to_out(
        row,
        await _signed(sb, row.get("original_photo_url")),
        await _signed(sb, row.get("result_photo_url")),
    )


@router.post("/{generation_id}/retry", response_model=GenerationOut, status_code=202)
async def retry_generation(
    generation_id: str,
    body: RetryRequest,
    background: BackgroundTasks,
    user: CurrentUser = Depends(get_current_user),
) -> GenerationOut:
    sb = get_supabase()
    rows = await sb.select(
        "generations",
        filters={"id": f"eq.{generation_id}", "deleted_at": "is.null"},
        limit=1,
    )
    if not rows or rows[0]["user_id"] != user.id:
        raise HTTPException(status_code=404, detail="not_found")
    prev = rows[0]
    if not prev.get("photo_consent_id"):
        raise HTTPException(status_code=409, detail="photo_consent_required")
    style_id = str(body.style_id) if body.style_id else prev["style_id"]
    req = GenerateRequest(
        style_id=style_id,
        photo_consent_id=prev["photo_consent_id"],
        original_photo_path=prev["original_photo_url"],
    )
    return await start_generation(req, background, user)


async def _purge_with_receipt(sb: SupabaseClient, row: dict) -> PhotoDeletionOut:
    object_count = len(generation_photo_paths(row))
    try:
        outcome = await purge_generation_photos(sb, row, reason="deleted_by_user")
        return PhotoDeletionOut(
            generation_id=row["id"],
            status="deleted",
            object_count=outcome.object_count,
        )
    except SupabaseError:
        try:
            current = await sb.select(
                "generations",
                filters={"id": f"eq.{row['id']}"},
                limit=1,
            )
        except SupabaseError:
            raise
        if current and current[0].get("photo_deletion_pending"):
            return PhotoDeletionOut(
                generation_id=row["id"],
                status="pending",
                object_count=object_count,
            )
        raise


@router.delete("", response_model=PhotoDeletionSummary)
async def delete_all_generation_photos(
    user: CurrentUser = Depends(get_current_user),
) -> PhotoDeletionSummary:
    sb = get_supabase()
    rows = await sb.select(
        "generations",
        filters={
            "user_id": f"eq.{user.id}",
            "or": "(deleted_at.is.null,photo_deletion_pending.eq.true)",
        },
    )
    deleted = 0
    pending = 0
    failed = 0
    objects_requested = 0
    for row in rows:
        objects_requested += len(generation_photo_paths(row))
        try:
            receipt = await _purge_with_receipt(sb, row)
        except SupabaseError:
            failed += 1
            log.exception("photo deletion could not be recorded for generation %s", row["id"])
            continue
        if receipt.status == "deleted":
            deleted += 1
        else:
            pending += 1

    return PhotoDeletionSummary(
        requested=len(rows),
        deleted=deleted,
        pending=pending,
        failed=failed,
        objects_requested=objects_requested,
    )


@router.delete("/{generation_id}", response_model=PhotoDeletionOut)
async def delete_generation(
    generation_id: str, user: CurrentUser = Depends(get_current_user)
) -> PhotoDeletionOut:
    sb = get_supabase()
    rows = await sb.select("generations", filters={"id": f"eq.{generation_id}"}, limit=1)
    if not rows or rows[0]["user_id"] != user.id:
        raise HTTPException(status_code=404, detail="not_found")
    try:
        return await _purge_with_receipt(sb, rows[0])
    except SupabaseError as exc:
        log.exception("photo deletion could not be recorded for generation %s", generation_id)
        raise HTTPException(status_code=503, detail="photo_deletion_unconfirmed") from exc
