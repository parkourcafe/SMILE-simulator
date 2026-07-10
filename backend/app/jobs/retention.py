"""Scheduled hard-delete job for expired or previously failed photo deletions.

Run from the backend directory:

    python -m app.jobs.retention --dry-run
    python -m app.jobs.retention --limit 100
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta

from app.config import Settings, get_settings
from app.services.retention import DeletionReason, purge_generation_photos
from app.services.supabase_client import SupabaseClient, get_supabase

log = logging.getLogger("smile.retention")


@dataclass(frozen=True)
class RetentionRunResult:
    scanned: int
    purged: int
    failed: int
    objects_requested: int
    dry_run: bool
    cutoff: str


def _reason(row: dict) -> DeletionReason:
    value = row.get("photo_deletion_reason")
    if value in {"deleted_by_user", "retention_expired", "account_deleted"}:
        return value
    return "retention_expired"


async def run_retention(
    *,
    settings: Settings | None = None,
    sb: SupabaseClient | None = None,
    dry_run: bool = False,
    limit: int = 100,
    now: datetime | None = None,
) -> RetentionRunResult:
    settings = settings or get_settings()
    sb = sb or get_supabase()
    if not sb.configured:
        raise RuntimeError("Supabase is not configured for the retention job.")
    if not 1 <= limit <= 1000:
        raise ValueError("limit must be between 1 and 1000")

    run_at = now or datetime.now(UTC)
    cutoff = run_at - timedelta(days=settings.photo_retention_days)
    # Retry any explicit deletion request immediately. Otherwise select rows whose
    # retention window expired and that have not already been tombstoned.
    filters = {
        "or": (
            "(photo_deletion_pending.eq.true,"
            f"and(deleted_at.is.null,created_at.lt.{cutoff.isoformat()}))"
        ),
        "order": "created_at.asc",
    }
    rows = await sb.select("generations", filters=filters, limit=limit)

    purged = 0
    failed = 0
    objects_requested = 0
    for row in rows:
        try:
            outcome = await purge_generation_photos(
                sb,
                row,
                reason=_reason(row),
                dry_run=dry_run,
                now=run_at,
            )
            objects_requested += outcome.object_count
            if not dry_run:
                purged += 1
        except Exception:  # noqa: BLE001 - continue so one bad object does not stop the batch
            failed += 1
            log.exception("photo purge failed for generation %s", row.get("id"))

    return RetentionRunResult(
        scanned=len(rows),
        purged=purged,
        failed=failed,
        objects_requested=objects_requested,
        dry_run=dry_run,
        cutoff=cutoff.isoformat(),
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Delete expired ZubiLook photo objects.")
    parser.add_argument("--dry-run", action="store_true", help="Report without deleting.")
    parser.add_argument("--limit", type=int, default=100, help="Rows per scheduled run (1-1000).")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    result = asyncio.run(run_retention(dry_run=args.dry_run, limit=args.limit))
    print(json.dumps(asdict(result), sort_keys=True))
    return 1 if result.failed else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
