"""Release generation reservations left behind by a crashed inference worker.

Run every five minutes from the backend directory:

    python -m app.jobs.quota_reconciliation --dry-run
    python -m app.jobs.quota_reconciliation --limit 100
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta

from app.config import Settings, get_settings
from app.services.supabase_client import SupabaseClient, get_supabase

log = logging.getLogger("smile.quota_reconciliation")


@dataclass(frozen=True)
class QuotaReconciliationResult:
    scanned: int
    released: int
    failed: int
    dry_run: bool
    cutoff: str


async def reconcile_stale_reservations(
    *,
    settings: Settings | None = None,
    sb: SupabaseClient | None = None,
    dry_run: bool = False,
    limit: int = 100,
    now: datetime | None = None,
) -> QuotaReconciliationResult:
    settings = settings or get_settings()
    sb = sb or get_supabase()
    if not sb.configured:
        raise RuntimeError("Supabase is not configured for quota reconciliation.")
    if not 1 <= limit <= 1000:
        raise ValueError("limit must be between 1 and 1000")
    if not 5 <= settings.generation_reservation_timeout_minutes <= 60:
        raise ValueError("generation reservation timeout must be between 5 and 60 minutes")

    run_at = now or datetime.now(UTC)
    cutoff = run_at - timedelta(minutes=settings.generation_reservation_timeout_minutes)
    rows = await sb.select(
        "generations",
        filters={
            "quota_state": "eq.reserved",
            "status": "in.(pending,processing)",
            "deleted_at": "is.null",
            "quota_reserved_at": f"lt.{cutoff.isoformat()}",
            "order": "quota_reserved_at.asc",
        },
        limit=limit,
    )

    released = 0
    failed = 0
    if not dry_run:
        for row in rows:
            try:
                updated = await sb.update(
                    "generations",
                    filters={
                        "id": f"eq.{row['id']}",
                        "quota_state": "eq.reserved",
                        "status": "in.(pending,processing)",
                    },
                    patch={
                        "status": "failed",
                        "error_message": "quota_reservation_expired",
                    },
                )
                if updated:
                    released += 1
            except Exception:  # noqa: BLE001 - continue so one row cannot block the batch
                failed += 1
                log.exception("quota reconciliation failed for generation %s", row.get("id"))

    return QuotaReconciliationResult(
        scanned=len(rows),
        released=released,
        failed=failed,
        dry_run=dry_run,
        cutoff=cutoff.isoformat(),
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Release stale generation reservations.")
    parser.add_argument("--dry-run", action="store_true", help="Report without updating rows.")
    parser.add_argument("--limit", type=int, default=100, help="Rows per run (1-1000).")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    result = asyncio.run(reconcile_stale_reservations(dry_run=args.dry_run, limit=args.limit))
    print(json.dumps(asdict(result), sort_keys=True))
    return 1 if result.failed else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
