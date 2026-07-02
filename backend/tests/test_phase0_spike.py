"""Smoke test for the Phase 0 spike runner in --dry-run mode (no Fal.ai)."""

from __future__ import annotations

import csv
import importlib
import sys
from pathlib import Path

import pytest

# scripts/ lives at the repo root (sibling of backend/), so go up two levels.
SCRIPT_DIR = Path(__file__).resolve().parents[2] / "scripts" / "phase0"


@pytest.fixture
def spike_module():
    sys.path.insert(0, str(SCRIPT_DIR))
    mod = importlib.import_module("run_spike")
    try:
        yield mod
    finally:
        sys.path.remove(str(SCRIPT_DIR))


@pytest.mark.asyncio
async def test_dry_run_produces_reports(spike_module, selfie_bytes, tmp_path):
    in_dir = tmp_path / "in"
    out_dir = tmp_path / "out"
    in_dir.mkdir()
    (in_dir / "selfie_0.png").write_bytes(selfie_bytes)

    rows = await spike_module.run_spike(
        in_dir, out_dir, ["natural_white", "hollywood_smile"], dry_run=True
    )

    assert len(rows) == 2
    assert all(r["status"] == "ok" for r in rows)

    # reports written
    assert (out_dir / "results.csv").exists()
    assert (out_dir / "scorecard.csv").exists()
    assert (out_dir / "summary.txt").exists()
    # before/after pair created
    assert (out_dir / "selfie_0__natural_white__compare.png").exists()

    # scorecard has the 5 criteria columns
    with (out_dir / "scorecard.csv").open() as f:
        header = next(csv.reader(f))
    for col in [
        "tooth_realism",
        "face_preservation",
        "boundary_blending",
        "style_accuracy",
        "emotional_response",
    ]:
        assert col in header
