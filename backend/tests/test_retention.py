from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.config import Settings
from app.jobs.retention import run_retention
from app.routers import generate
from app.routers.generate import _validate_owned_photo_path
from app.services.quota import QuotaDecision
from app.services.retention import generation_photo_paths, purge_generation_photos
from app.services.supabase_client import SupabaseError


class FakeSupabase:
    configured = True

    def __init__(self, rows: list[dict] | None = None, *, fail_remove: bool = False):
        self.rows = rows or []
        self.fail_remove = fail_remove
        self.updates: list[tuple[str, dict[str, str], dict]] = []
        self.removals: list[list[str]] = []
        self.select_filters: dict[str, str] | None = None

    async def select(self, table, *, filters=None, limit=None):
        assert table == "generations"
        self.select_filters = filters
        return self.rows[:limit]

    async def update(self, table, *, filters, patch):
        self.updates.append((table, filters, patch))
        generation_id = filters.get("id", "").removeprefix("eq.")
        for row in self.rows:
            if not generation_id or str(row.get("id")) == generation_id:
                row.update(patch)
        return [patch]

    async def remove_objects(self, paths):
        self.removals.append(paths)
        if self.fail_remove:
            raise SupabaseError("storage unavailable")
        return [{"name": path} for path in paths]


def _row(**overrides) -> dict:
    row = {
        "id": "generation-1",
        "user_id": "user-1",
        "original_photo_url": "user-1/original.jpg",
        "deleted_at": None,
        "photo_deleted_at": None,
    }
    row.update(overrides)
    row.setdefault("result_photo_url", f"{row['user_id']}/{row['id']}_result.png")
    row.setdefault("mask_url", f"{row['user_id']}/{row['id']}_mask.png")
    return row


def test_generation_paths_include_in_flight_deterministic_objects():
    assert generation_photo_paths(_row(result_photo_url=None, mask_url=None)) == [
        "user-1/original.jpg",
        "user-1/generation-1_result.png",
        "user-1/generation-1_mask.png",
    ]


@pytest.mark.asyncio
async def test_photo_purge_marks_pending_deletes_storage_and_tombstones_row():
    sb = FakeSupabase()
    now = datetime(2026, 7, 10, 6, 0, tzinfo=UTC)

    outcome = await purge_generation_photos(
        sb,
        _row(),
        reason="deleted_by_user",
        now=now,
    )

    assert outcome.object_count == 3
    assert sb.removals == [
        [
            "user-1/original.jpg",
            "user-1/generation-1_result.png",
            "user-1/generation-1_mask.png",
        ]
    ]
    assert sb.updates[0][2]["photo_deletion_pending"] is True
    assert sb.updates[0][2]["deleted_at"] == now.isoformat()
    assert sb.updates[1][2] == {
        "original_photo_url": None,
        "result_photo_url": None,
        "mask_url": None,
        "prompt": None,
        "photo_deletion_pending": False,
        "photo_deleted_at": now.isoformat(),
    }


@pytest.mark.asyncio
async def test_failed_storage_delete_remains_pending_for_retry():
    sb = FakeSupabase(fail_remove=True)
    with pytest.raises(SupabaseError):
        await purge_generation_photos(sb, _row(), reason="deleted_by_user")
    assert len(sb.updates) == 1
    assert sb.updates[0][2]["photo_deletion_pending"] is True


@pytest.mark.asyncio
async def test_dry_run_does_not_mutate_data():
    sb = FakeSupabase()
    outcome = await purge_generation_photos(
        sb,
        _row(),
        reason="retention_expired",
        dry_run=True,
    )
    assert outcome.dry_run is True
    assert not sb.updates
    assert not sb.removals


@pytest.mark.asyncio
async def test_retention_job_processes_expired_and_pending_rows():
    sb = FakeSupabase(
        [
            _row(),
            _row(
                id="generation-2",
                photo_deletion_reason="deleted_by_user",
                photo_deletion_pending=True,
            ),
        ]
    )
    result = await run_retention(
        settings=Settings(photo_retention_days=30),
        sb=sb,
        now=datetime(2026, 7, 10, tzinfo=UTC),
    )
    assert result.scanned == 2
    assert result.purged == 2
    assert result.failed == 0
    assert result.objects_requested == 6
    assert "photo_deletion_pending.eq.true" in sb.select_filters["or"]
    assert "created_at.lt.2026-06-10" in sb.select_filters["or"]


@pytest.mark.asyncio
async def test_retention_job_dry_run_reports_without_claiming_purge():
    sb = FakeSupabase([_row()])
    result = await run_retention(
        settings=Settings(photo_retention_days=30),
        sb=sb,
        dry_run=True,
        now=datetime(2026, 7, 10, tzinfo=UTC),
    )
    assert result.scanned == 1
    assert result.purged == 0
    assert result.objects_requested == 3
    assert not sb.updates
    assert not sb.removals


@pytest.mark.parametrize(
    "path",
    [
        "other-user/photo.jpg",
        "/user-1/photo.jpg",
        "user-1/../other-user/photo.jpg",
        "user-1\\photo.jpg",
        "photo.jpg",
    ],
)
def test_generation_rejects_unowned_or_unsafe_photo_paths(path):
    with pytest.raises(HTTPException) as exc:
        _validate_owned_photo_path(path, "user-1")
    assert exc.value.status_code == 422


def test_generation_accepts_user_owned_photo_path():
    _validate_owned_photo_path("user-1/uploads/photo.jpg", "user-1")


@pytest.mark.asyncio
async def test_user_delete_returns_verified_storage_status(monkeypatch):
    generation_id = "0bc2b9e6-c910-4f3c-b86b-a144313805f7"
    sb = FakeSupabase([_row(id=generation_id)])
    monkeypatch.setattr(generate, "get_supabase", lambda: sb)

    receipt = await generate.delete_generation(
        generation_id,
        SimpleNamespace(id="user-1"),
    )

    assert receipt.status == "deleted"
    assert receipt.object_count == 3


@pytest.mark.asyncio
async def test_user_delete_reports_retryable_storage_failure_as_pending(monkeypatch):
    generation_id = "1a6ee371-9280-480b-9fd8-8506b50be585"
    sb = FakeSupabase([_row(id=generation_id)], fail_remove=True)
    monkeypatch.setattr(generate, "get_supabase", lambda: sb)

    receipt = await generate.delete_generation(
        generation_id,
        SimpleNamespace(id="user-1"),
    )

    assert receipt.status == "pending"
    assert sb.rows[0]["deleted_at"] is not None
    assert sb.rows[0]["photo_deletion_pending"] is True


@pytest.mark.asyncio
async def test_user_can_request_deletion_of_all_generation_photos(monkeypatch):
    sb = FakeSupabase(
        [
            _row(id="6dcfdd9d-68f9-4104-89f0-2d0315e7274e"),
            _row(id="e7049b90-ff74-40fb-b5ed-bfc90f5927d3"),
        ]
    )
    monkeypatch.setattr(generate, "get_supabase", lambda: sb)

    summary = await generate.delete_all_generation_photos(SimpleNamespace(id="user-1"))

    assert summary.requested == 2
    assert summary.deleted == 2
    assert summary.pending == 0
    assert summary.failed == 0
    assert summary.objects_requested == 6
    assert sb.select_filters["user_id"] == "eq.user-1"


class ProcessingSupabase:
    def __init__(self, *, deleted_before_upload: bool):
        self.deleted_before_upload = deleted_before_upload
        self.uploads: list[str] = []
        self.removals: list[list[str]] = []

    async def update(self, _table, *, filters, patch):
        if patch.get("status") == "completed":
            return []
        return [patch]

    async def download(self, _path):
        return b"original"

    async def select(self, _table, *, filters, limit):
        return [{"deleted_at": "2026-07-10T00:00:00+00:00" if self.deleted_before_upload else None}]

    async def upload(self, path, _data):
        self.uploads.append(path)

    async def remove_objects(self, paths):
        self.removals.append(paths)
        return []


async def _pipeline_result(**_kwargs):
    return SimpleNamespace(
        result_image=b"result",
        mask_image=b"mask",
        prompt="prompt",
        provider="test",
        cost_usd=0.0,
        duration_ms=1,
        quality_score=5.0,
    )


@pytest.mark.asyncio
async def test_processing_stops_when_generation_was_deleted(monkeypatch):
    sb = ProcessingSupabase(deleted_before_upload=True)
    monkeypatch.setattr(generate, "get_supabase", lambda: sb)
    monkeypatch.setattr(generate, "run_pipeline", _pipeline_result)

    await generate._process(
        "generation-1",
        "user-1",
        "user-1/original.jpg",
        {"prompt_template": "template", "name": "Natural"},
        False,
        QuotaDecision(allowed=True, watermark=False, pack_id=None),
    )
    assert not sb.uploads
    assert not sb.removals


@pytest.mark.asyncio
async def test_processing_removes_uploaded_result_when_tombstone_wins_race(monkeypatch):
    sb = ProcessingSupabase(deleted_before_upload=False)
    monkeypatch.setattr(generate, "get_supabase", lambda: sb)
    monkeypatch.setattr(generate, "run_pipeline", _pipeline_result)

    await generate._process(
        "generation-1",
        "user-1",
        "user-1/original.jpg",
        {"prompt_template": "template", "name": "Natural"},
        False,
        QuotaDecision(allowed=True, watermark=False, pack_id=None),
    )
    assert sb.uploads == [
        "user-1/generation-1_result.png",
        "user-1/generation-1_mask.png",
    ]
    assert sb.removals == [
        [
            "user-1/generation-1_result.png",
            "user-1/generation-1_mask.png",
        ]
    ]
