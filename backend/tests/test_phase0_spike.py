"""Smoke test for the Phase 0 spike runner in --dry-run mode (no Fal.ai)."""

from __future__ import annotations

import csv
import hashlib
import importlib
import json
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

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
    image = in_dir / "selfie_0.png"
    image.write_bytes(selfie_bytes)
    rows = await spike_module.run_spike(
        [image],
        out_dir,
        ["natural_white", "hollywood_smile"],
        {image.name: hashlib.sha256(selfie_bytes).hexdigest()},
        dry_run=True,
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


@pytest.fixture
def evidence_module():
    sys.path.insert(0, str(SCRIPT_DIR))
    mod = importlib.import_module("evidence")
    try:
        yield mod
    finally:
        sys.path.remove(str(SCRIPT_DIR))


def _write_consent_manifest(path, filenames):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "file",
                "consent_confirmed",
                "consent_version",
                "consented_at",
                "deletion_due_at",
            ]
        )
        for filename in filenames:
            writer.writerow([filename, "true", "phase0-test-v1", "2026-07-10", "2026-08-09"])


def test_preflight_requires_exact_unique_consented_inputs(evidence_module, tmp_path):
    images = []
    for index in range(10):
        path = tmp_path / f"selfie_{index:02}.png"
        path.write_bytes(f"image-{index}".encode())
        images.append(path)
    consent_path = tmp_path / "consent_manifest.csv"
    _write_consent_manifest(consent_path, {path.name for path in images})
    consents = evidence_module.load_consent_manifest(
        consent_path,
        {path.name for path in images},
        today=date(2026, 7, 10),
    )

    records = evidence_module.build_input_evidence(
        images,
        inspect_image=lambda _path: (1024, 1024, False),
        consents=consents,
    )

    assert len(records) == 10
    assert all(record.consent_confirmed for record in records)
    assert all(record.face_approximate is False for record in records)


def test_preflight_rejects_exact_duplicate_images(evidence_module, tmp_path):
    first = tmp_path / "selfie_01.png"
    second = tmp_path / "selfie_02.png"
    first.write_bytes(b"same")
    second.write_bytes(b"same")

    with pytest.raises(evidence_module.EvidenceError, match="Exact duplicate"):
        evidence_module.build_input_evidence(
            [first, second],
            inspect_image=lambda _path: (1024, 1024, False),
            consents=None,
            expected_count=2,
            require_real_landmarks=False,
        )


def _write_evaluation_files(evidence_module, tmp_path, *, failed=0, score=4.0):
    results_path = tmp_path / "results.csv"
    scorecard_path = tmp_path / "scorecard.csv"
    with results_path.open("w", newline="", encoding="utf-8") as handle:
        fields = [
            "file",
            "input_sha256",
            "style",
            "status",
            "provider",
            "request_id",
            "cost_usd",
            "duration_ms",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for index in range(10):
            writer.writerow(
                {
                    "file": f"selfie_{index:02}.png",
                    "input_sha256": f"hash-{index}",
                    "style": "natural_white",
                    "status": "error" if index < failed else "ok",
                    "provider": "fal_flux_pro_fill",
                    "request_id": "" if index < failed else f"request-{index}",
                    "cost_usd": "0.10",
                    "duration_ms": "5000",
                }
            )
    (tmp_path / "run_config.json").write_text(
        json.dumps(
            {
                "dry_run": False,
                "watermark": False,
                "source_dirty": False,
                "source_commit": "a" * 40,
                "input_count": 10,
                "styles": ["natural_white"],
                "face_model_sha256": evidence_module.EXPECTED_FACE_MODEL_SHA256,
                "endpoint": evidence_module.EXPECTED_ENDPOINT,
                "result_image_size": 1024,
            }
        ),
        encoding="utf-8",
    )
    with (tmp_path / "input_manifest.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = [
            "file",
            "sha256",
            "consent_confirmed",
            "consent_version",
            "consented_at",
            "deletion_due_at",
            "face_approximate",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for index in range(10):
            writer.writerow(
                {
                    "file": f"selfie_{index:02}.png",
                    "sha256": f"hash-{index}",
                    "consent_confirmed": True,
                    "consent_version": "phase0-test-v1",
                    "consented_at": "2026-07-10",
                    "deletion_due_at": "2026-08-09",
                    "face_approximate": False,
                }
            )
    with scorecard_path.open("w", newline="", encoding="utf-8") as handle:
        fields = ["file", "style", *evidence_module.CRITERIA, "avg", "notes"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for index in range(failed, 10):
            writer.writerow(
                {
                    "file": f"selfie_{index:02}.png",
                    "style": "natural_white",
                    **{criterion: score for criterion in evidence_module.CRITERIA},
                    "avg": score,
                    "notes": "",
                }
            )
    return results_path, scorecard_path


def test_scorecard_evaluator_emits_go_only_for_complete_standard_run(evidence_module, tmp_path):
    results, scorecard = _write_evaluation_files(evidence_module, tmp_path)

    evaluation = evidence_module.evaluate_scorecard(results, scorecard)

    assert evaluation.decision == "GO"
    assert evaluation.overall_average == 4.0
    assert evaluation.request_ids_captured == 10
    report = evidence_module.render_report(
        evaluation,
        now=datetime(2026, 7, 10, 20, 0, tzinfo=ZoneInfo("Asia/Makassar")),
    )
    assert "> Created: 10.07.2026 | 20:00 | Bali" in report
    assert "> Decision: **GO**" in report
    assert "run_config.json" in report


def test_dry_run_configuration_cannot_produce_go(evidence_module, tmp_path):
    results, scorecard = _write_evaluation_files(evidence_module, tmp_path)
    config_path = tmp_path / "run_config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["dry_run"] = True
    config_path.write_text(json.dumps(config), encoding="utf-8")

    evaluation = evidence_module.evaluate_scorecard(results, scorecard)

    assert evaluation.decision == "ITERATE"
    assert any("run_config.json" in reason for reason in evaluation.reasons)


def test_failed_generation_blocks_go_and_identity_failure_forces_no_go(evidence_module, tmp_path):
    results, scorecard = _write_evaluation_files(evidence_module, tmp_path, failed=1)
    evaluation = evidence_module.evaluate_scorecard(results, scorecard)
    forced = evidence_module.evaluate_scorecard(
        results,
        scorecard,
        recurring_identity_failure=True,
    )

    assert evaluation.decision == "ITERATE"
    assert forced.decision == "NO-GO"
