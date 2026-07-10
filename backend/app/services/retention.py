"""Idempotent photo deletion for user requests and the 30-day retention job."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from app.services.supabase_client import SupabaseClient

DeletionReason = Literal["deleted_by_user", "retention_expired", "account_deleted"]
PHOTO_PATH_FIELDS = ("original_photo_url", "result_photo_url", "mask_url")


@dataclass(frozen=True)
class PurgeOutcome:
    generation_id: str
    reason: DeletionReason
    object_count: int
    dry_run: bool


def generation_photo_paths(row: dict) -> list[str]:
    """Return unique object paths, including deterministic in-flight result paths."""
    paths = [row.get(field) for field in PHOTO_PATH_FIELDS]
    if row.get("user_id") and row.get("id"):
        prefix = f"{row['user_id']}/{row['id']}"
        paths.extend([f"{prefix}_result.png", f"{prefix}_mask.png"])
    return list(dict.fromkeys(value for value in paths if isinstance(value, str) and value))


async def purge_generation_photos(
    sb: SupabaseClient,
    row: dict,
    *,
    reason: DeletionReason,
    dry_run: bool = False,
    now: datetime | None = None,
) -> PurgeOutcome:
    """Delete all photo objects and retain a minimal, non-image generation tombstone.

    The row is marked pending before Storage deletion. If Storage or the final update
    fails, a later retention run sees ``photo_deletion_pending=true`` and retries.
    """
    generation_id = str(row["id"])
    paths = generation_photo_paths(row)
    if dry_run:
        return PurgeOutcome(generation_id, reason, len(paths), True)

    timestamp = (now or datetime.now(UTC)).isoformat()
    pending_patch: dict = {
        "status": "failed",
        "error_message": reason,
        "photo_deletion_pending": True,
        "photo_deletion_reason": reason,
    }
    if not row.get("deleted_at"):
        pending_patch["deleted_at"] = timestamp

    await sb.update(
        "generations",
        filters={"id": f"eq.{generation_id}"},
        patch=pending_patch,
    )
    await sb.remove_objects(paths)
    await sb.update(
        "generations",
        filters={"id": f"eq.{generation_id}"},
        patch={
            "original_photo_url": None,
            "result_photo_url": None,
            "mask_url": None,
            "prompt": None,
            "photo_deletion_pending": False,
            "photo_deleted_at": row.get("photo_deleted_at") or timestamp,
        },
    )
    return PurgeOutcome(generation_id, reason, len(paths), False)
