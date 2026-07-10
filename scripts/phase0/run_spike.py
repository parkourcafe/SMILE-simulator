#!/usr/bin/env python3
"""Run the standardized, auditable ZubiLook Phase 0 inpainting test."""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import io
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

# Make the backend package importable when run directly from scripts/phase0.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from evidence import (  # noqa: E402
    EvidenceError,
    build_input_evidence,
    collect_images,
    load_consent_manifest,
    write_input_manifest,
)
from PIL import Image  # noqa: E402
from styles import STYLES  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.ml import face_mesh, photo, pipeline  # noqa: E402
from app.ml.providers.base import GenerationResult  # noqa: E402

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}


class _DryRunProvider:
    """Echo the input so preflight/reporting can be tested without Fal.ai."""

    name = "dryrun"

    async def generate(self, *, image, mask, prompt, config):  # noqa: ANN001
        return GenerationResult(image=image, cost_usd=0.0, duration_ms=0, provider="dryrun")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _side_by_side(before: Image.Image, after: Image.Image) -> Image.Image:
    height = max(before.height, after.height)
    before = before.resize((int(before.width * height / before.height), height))
    after = after.resize((int(after.width * height / after.height), height))
    canvas = Image.new("RGB", (before.width + after.width + 12, height), (255, 255, 255))
    canvas.paste(before, (0, 0))
    canvas.paste(after, (before.width + 12, 0))
    return canvas


def _inspect_image(path: Path) -> tuple[int, int, bool]:
    original = photo.load_and_validate(path.read_bytes())
    _, landmarks = face_mesh.detect_and_crop(
        original,
        size=get_settings().result_image_size,
    )
    return original.width, original.height, landmarks.approximate


def _git_state() -> tuple[str, bool]:
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(__file__).resolve().parents[2],
            check=True,
            capture_output=True,
            text=True,
        )
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=Path(__file__).resolve().parents[2],
            check=True,
            capture_output=True,
            text=True,
        )
        return commit.stdout.strip(), bool(status.stdout.strip())
    except (OSError, subprocess.CalledProcessError):
        return "unknown", True


def _write_run_config(
    output_dir: Path,
    *,
    style_keys: list[str],
    input_count: int,
    dry_run: bool,
    watermark: bool,
) -> None:
    settings = get_settings()
    source_commit, source_dirty = _git_state()
    model_path = settings.face_model_path
    model_hash = _sha256(model_path.read_bytes()) if model_path.is_file() else ""
    config = {
        "created_at": datetime.now(UTC).isoformat(),
        "source_commit": source_commit,
        "source_dirty": source_dirty,
        "provider": "dryrun" if dry_run else settings.inference_provider,
        "endpoint": "" if dry_run else settings.fal_flux_fill_endpoint,
        "styles": style_keys,
        "input_count": input_count,
        "result_image_size": settings.result_image_size,
        "watermark": watermark,
        "dry_run": dry_run,
        "face_model_sha256": model_hash,
        "prompt_template_sha256": {key: _sha256(STYLES[key].encode("utf-8")) for key in style_keys},
    }
    (output_dir / "run_config.json").write_text(
        json.dumps(config, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


async def _run_one(
    path: Path,
    style_key: str,
    output_dir: Path,
    *,
    input_sha256: str,
    watermark: bool,
) -> dict:
    template = STYLES[style_key]
    stem = path.stem
    result_file = f"{stem}__{style_key}.png"
    compare_file = f"{stem}__{style_key}__compare.png"
    row = {
        "file": path.name,
        "input_sha256": input_sha256,
        "style": style_key,
        "status": "ok",
        "provider": "",
        "request_id": "",
        "cost_usd": 0.0,
        "duration_ms": 0,
        "quality_heuristic": "",
        "face_approximate": "",
        "prompt_sha256": "",
        "result_sha256": "",
        "mask_sha256": "",
        "result_file": result_file,
        "compare_file": compare_file,
        "error": "",
    }
    try:
        photo_bytes = path.read_bytes()
        output = await pipeline.run_pipeline(
            photo_bytes=photo_bytes,
            style_template=template,
            style_name=style_key.replace("_", " ").title(),
            apply_watermark=watermark,
        )
        result_image = Image.open(io.BytesIO(output.result_image)).convert("RGB")
        result_image.save(output_dir / result_file)

        before = pipeline.photo.normalize(pipeline.photo.load_and_validate(photo_bytes))
        _side_by_side(before, result_image).save(output_dir / compare_file)

        row.update(
            provider=output.provider,
            request_id=output.request_id or "",
            cost_usd=output.cost_usd,
            duration_ms=output.duration_ms,
            quality_heuristic=output.quality_score,
            face_approximate=output.face_approximate,
            prompt_sha256=_sha256(output.prompt.encode("utf-8")),
            result_sha256=_sha256(output.result_image),
            mask_sha256=_sha256(output.mask_image),
        )
    except Exception as exc:  # noqa: BLE001 - preserve the batch and record the failure
        row["status"] = "error"
        row["error"] = f"{type(exc).__name__}: {exc}"[:300]
    return row


async def run_spike(
    images: list[Path],
    output_dir: Path,
    style_keys: list[str],
    input_hashes: dict[str, str],
    *,
    dry_run: bool = False,
    watermark: bool = False,
) -> list[dict]:
    output_dir.mkdir(parents=True, exist_ok=True)
    if dry_run:
        pipeline.get_provider = lambda name=None: _DryRunProvider()

    rows: list[dict] = []
    for path in images:
        for style_key in style_keys:
            print(f"  {path.name} · {style_key} ...", flush=True)
            rows.append(
                await _run_one(
                    path,
                    style_key,
                    output_dir,
                    input_sha256=input_hashes[path.name],
                    watermark=watermark,
                )
            )

    _write_reports(output_dir, rows)
    return rows


def _write_reports(output_dir: Path, rows: list[dict]) -> None:
    fields = [
        "file",
        "input_sha256",
        "style",
        "status",
        "provider",
        "request_id",
        "cost_usd",
        "duration_ms",
        "quality_heuristic",
        "face_approximate",
        "prompt_sha256",
        "result_sha256",
        "mask_sha256",
        "result_file",
        "compare_file",
        "error",
    ]
    with (output_dir / "results.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    criteria = [
        "tooth_realism",
        "face_preservation",
        "boundary_blending",
        "style_accuracy",
        "emotional_response",
    ]
    with (output_dir / "scorecard.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["file", "style", *criteria, "avg", "notes"])
        for row in rows:
            if row["status"] == "ok":
                writer.writerow([row["file"], row["style"], *([""] * len(criteria)), "", ""])

    successful = [row for row in rows if row["status"] == "ok"]
    total_cost = sum(float(row["cost_usd"] or 0) for row in rows)
    average_ms = (
        sum(int(row["duration_ms"] or 0) for row in successful) / len(successful)
        if successful
        else 0
    )
    summary = (
        "Phase 0 execution summary\n"
        f"  generations attempted : {len(rows)}\n"
        f"  succeeded             : {len(successful)}\n"
        f"  failed                : {len(rows) - len(successful)}\n"
        f"  total measured cost   : ${total_cost:.4f}\n"
        f"  average duration      : {average_ms:.0f} ms\n"
        "\nNo decision has been made yet. Complete scorecard.csv, then run:\n"
        "  python scripts/phase0/evaluate_scorecard.py --results OUT/results.csv "
        "--scorecard OUT/scorecard.csv --output OUT/PHASE0_REPORT.md\n"
    )
    (output_dir / "summary.txt").write_text(summary, encoding="utf-8")
    print("\n" + summary)


def _parse_styles(value: str) -> list[str]:
    if value.strip().lower() == "all":
        return list(STYLES)
    keys = [style.strip() for style in value.split(",") if style.strip()]
    unknown = [key for key in keys if key not in STYLES]
    if unknown:
        raise EvidenceError(f"Unknown styles {unknown}. Available: {list(STYLES)}")
    return keys


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the standardized ZubiLook Phase 0 spike")
    parser.add_argument("--input", required=True, type=Path, help="folder of 10 selfies")
    parser.add_argument("--output", required=True, type=Path, help="new empty output folder")
    parser.add_argument(
        "--styles",
        default="natural_white",
        help="one fixed style for a real run; 'all' is allowed only for dry-run",
    )
    parser.add_argument(
        "--consent-manifest",
        type=Path,
        help="CSV path; defaults to INPUT/consent_manifest.csv",
    )
    parser.add_argument("--dry-run", action="store_true", help="no Fal.ai call; not valid evidence")
    parser.add_argument(
        "--allow-nonstandard-count",
        action="store_true",
        help="allow a non-10 input count only for dry-run harness tests",
    )
    parser.add_argument("--watermark", action="store_true", help="dry-run UI smoke only")
    args = parser.parse_args()

    try:
        style_keys = _parse_styles(args.styles)
        if not args.dry_run and len(style_keys) != 1:
            raise EvidenceError("A real Phase 0 run requires exactly one fixed style")
        if args.allow_nonstandard_count and not args.dry_run:
            raise EvidenceError("Non-standard input count is allowed only with --dry-run")
        if args.watermark and not args.dry_run:
            raise EvidenceError("The standardized real run must not use a watermark")
        if not args.dry_run and not os.environ.get("FAL_API_KEY"):
            raise EvidenceError("FAL_API_KEY is not set")
        if not args.dry_run and _git_state()[1]:
            raise EvidenceError("Source tree must be clean for a real evidence run")
        if not args.input.is_dir():
            raise EvidenceError(f"Input directory does not exist: {args.input}")
        if args.output.exists() and any(args.output.iterdir()):
            raise EvidenceError(f"Output directory must be empty: {args.output}")

        images = collect_images(args.input, IMAGE_EXTS)
        consent_path = args.consent_manifest or (args.input / "consent_manifest.csv")
        consents = None
        if consent_path.is_file():
            consents = load_consent_manifest(consent_path, {path.name for path in images})
        elif not args.dry_run:
            raise EvidenceError(f"Consent manifest is required: {consent_path}")

        records = build_input_evidence(
            images,
            inspect_image=_inspect_image,
            consents=consents,
            expected_count=None if args.allow_nonstandard_count else 10,
            require_real_landmarks=not args.dry_run,
        )
    except EvidenceError as exc:
        raise SystemExit(f"Phase 0 preflight failed: {exc}") from exc

    args.output.mkdir(parents=True, exist_ok=True)
    write_input_manifest(args.output / "input_manifest.csv", records)
    _write_run_config(
        args.output,
        style_keys=style_keys,
        input_count=len(images),
        dry_run=args.dry_run,
        watermark=args.watermark,
    )
    input_hashes = {record.file: record.sha256 for record in records}
    print(
        f"Preflight passed: {len(images)} image(s), {len(style_keys)} style(s)"
        f"{' [DRY RUN — NOT GATE EVIDENCE]' if args.dry_run else ''}\n"
    )
    asyncio.run(
        run_spike(
            images,
            args.output,
            style_keys,
            input_hashes,
            dry_run=args.dry_run,
            watermark=args.watermark,
        )
    )


if __name__ == "__main__":
    main()
