from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.config import Settings
from app.jobs.quota_reconciliation import reconcile_stale_reservations


class FakeSupabase:
    configured = True

    def __init__(self, rows):
        self.rows = rows
        self.select_filters = None
        self.updates = []

    async def select(self, table, *, filters=None, limit=None):
        assert table == "generations"
        self.select_filters = filters
        return self.rows[:limit]

    async def update(self, table, *, filters, patch):
        assert table == "generations"
        self.updates.append((filters, patch))
        return [{"id": filters["id"].removeprefix("eq.")}]


@pytest.mark.asyncio
async def test_reconciliation_fails_stale_rows_to_release_triggered_quota():
    sb = FakeSupabase([{"id": "generation-1"}, {"id": "generation-2"}])
    result = await reconcile_stale_reservations(
        settings=Settings(generation_reservation_timeout_minutes=15),
        sb=sb,
        now=datetime(2026, 7, 10, 9, 0, tzinfo=UTC),
    )

    assert result.scanned == 2
    assert result.released == 2
    assert result.failed == 0
    assert sb.select_filters["quota_reserved_at"] == "lt.2026-07-10T08:45:00+00:00"
    assert sb.updates[0][0]["quota_state"] == "eq.reserved"
    assert sb.updates[0][1] == {
        "status": "failed",
        "error_message": "quota_reservation_expired",
    }


@pytest.mark.asyncio
async def test_reconciliation_dry_run_does_not_update():
    sb = FakeSupabase([{"id": "generation-1"}])
    result = await reconcile_stale_reservations(
        settings=Settings(generation_reservation_timeout_minutes=15),
        sb=sb,
        dry_run=True,
        now=datetime(2026, 7, 10, 9, 0, tzinfo=UTC),
    )
    assert result.scanned == 1
    assert result.released == 0
    assert not sb.updates
