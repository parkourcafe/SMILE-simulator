#!/usr/bin/env python3
"""Phase 0 spike runner — test mouth inpainting on a folder of selfies.

Runs each selfie through the SAME pipeline that ships in production (normalize →
MediaPipe mouth mask → prompt → inference provider → quality heuristic), across one
or more styles. Produces, under the output dir:

  <stem>__<style>.png          inpainted result
  <stem>__<style>__compare.png before | after side-by-side (for the demo-pack)
  results.csv                  cost / duration / heuristic quality / errors
  scorecard.csv                pre-filled (file, style) + empty human-rating columns
  summary.txt                  totals: success rate, total cost, effective cost/good gen

Why a script for a "no-code" phase: testing OUR mask + prompt logic is more
predictive of MVP quality than poking the Fal.ai web playground by hand.

Usage:
  export FAL_API_KEY=...        # real run
  python run_spike.py --input ./selfies --output ./out --styles natural_white,hollywood_smile

  python run_spike.py --input ./selfies --output ./out --dry-run   # no key, no cost
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import io
import sys
from pathlib import Path

# Make the api-gateway package importable when run directly from scripts/phase0.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from PIL import Image  # noqa: E402

from app.ml import pipeline  # noqa: E402
from app.ml.providers.base import GenerationResult  # noqa: E402

from styles import STYLES  # noqa: E402  (local module)

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}


class _DryRunProvider:
    """Returns the input image unchanged — exercises mask/prompt/scoring without Fal.ai."""

    name = "dryrun"

    async def generate(self, *, image, mask, prompt, config):  # noqa: ANN001
        return GenerationResult(image=image, cost_usd=0.0, duration_ms=0, provider="dryrun")


def _side_by_side(before: Image.Image, after: Image.Image) -> Image.Image:
    h = max(before.height, after.height)
    before = before.resize((int(before.width * h / before.height), h))
    after = after.resize((int(after.width * h / after.height), h))
    canvas = Image.new("RGB", (before.width + after.width + 12, h), (255, 255, 255))
    canvas.paste(before, (0, 0))
    canvas.paste(after, (before.width + 12, 0))
    return canvas


async def _run_one(path: Path, style_key: str, out_dir: Path, watermark: bool) -> dict:
    template = STYLES[style_key]
    row = {
        "file": path.name,
        "style": style_key,
        "status": "ok",
        "cost_usd": 0.0,
        "duration_ms": 0,
        "quality_heuristic": "",
        "face_approximate": "",
        "error": "",
    }
    try:
        photo_bytes = path.read_bytes()
        out = await pipeline.run_pipeline(
            photo_bytes=photo_bytes,
            style_template=template,
            style_name=style_key.replace("_", " ").title(),
            apply_watermark=watermark,
        )
        stem = path.stem
        result_img = Image.open(io.BytesIO(out.result_image)).convert("RGB")
        result_img.save(out_dir / f"{stem}__{style_key}.png")

        before = pipeline.photo.normalize(pipeline.photo.load_and_validate(photo_bytes))
        _side_by_side(before, result_img).save(out_dir / f"{stem}__{style_key}__compare.png")

        row.update(
            cost_usd=out.cost_usd,
            duration_ms=out.duration_ms,
            quality_heuristic=out.quality_score,
            face_approximate=out.face_approximate,
        )
    except Exception as exc:  # noqa: BLE001 - record and continue with the next image
        row["status"] = "error"
        row["error"] = f"{type(exc).__name__}: {exc}"[:300]
    return row


async def run_spike(
    input_dir: Path,
    output_dir: Path,
    style_keys: list[str],
    *,
    dry_run: bool = False,
    watermark: bool = False,
) -> list[dict]:
    output_dir.mkdir(parents=True, exist_ok=True)
    images = sorted(p for p in input_dir.iterdir() if p.suffix.lower() in IMAGE_EXTS)
    if not images:
        raise SystemExit(f"No images found in {input_dir}")

    if dry_run:
        pipeline.get_provider = lambda name=None: _DryRunProvider()

    rows: list[dict] = []
    for path in images:
        for style_key in style_keys:
            print(f"  {path.name} · {style_key} ...", flush=True)
            rows.append(await _run_one(path, style_key, output_dir, watermark))

    _write_reports(output_dir, rows)
    return rows


def _write_reports(output_dir: Path, rows: list[dict]) -> None:
    # results.csv
    fields = [
        "file",
        "style",
        "status",
        "cost_usd",
        "duration_ms",
        "quality_heuristic",
        "face_approximate",
        "error",
    ]
    with (output_dir / "results.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    # scorecard.csv — human rating, 5 criteria (CLAUDE.md Quality Criteria / Brief §17.2)
    crit = [
        "tooth_realism",
        "face_preservation",
        "boundary_blending",
        "style_accuracy",
        "emotional_response",
    ]
    with (output_dir / "scorecard.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["file", "style", *crit, "avg", "notes"])
        for r in rows:
            if r["status"] == "ok":
                w.writerow([r["file"], r["style"], *([""] * len(crit)), "", ""])

    # summary.txt
    ok = [r for r in rows if r["status"] == "ok"]
    total_cost = sum(float(r["cost_usd"] or 0) for r in rows)
    avg_ms = sum(int(r["duration_ms"] or 0) for r in ok) / len(ok) if ok else 0
    success_rate = len(ok) / len(rows) if rows else 0
    eff_cost = total_cost / len(ok) if ok else 0
    approx = sum(1 for r in ok if r["face_approximate"] is True or r["face_approximate"] == "True")

    summary = (
        "Phase 0 spike summary\n"
        f"  generations attempted : {len(rows)}\n"
        f"  succeeded             : {len(ok)}\n"
        f"  success rate          : {success_rate:.0%}\n"
        f"  total inference cost  : ${total_cost:.3f}\n"
        f"  effective cost/good   : ${eff_cost:.3f}\n"
        f"  avg duration          : {avg_ms:.0f} ms\n"
        f"  approx-mask (no mediapipe): {approx} (install the 'ml' extra for real landmarks)\n"
        "\nNext: open scorecard.csv, rate each pair 1-5 on the 5 criteria.\n"
        "Go/No-Go: avg >= 3.5 and no criterion < 2.0 -> proceed to closed beta.\n"
    )
    (output_dir / "summary.txt").write_text(summary)
    print("\n" + summary)


def _parse_styles(value: str) -> list[str]:
    if value.strip().lower() == "all":
        return list(STYLES)
    keys = [s.strip() for s in value.split(",") if s.strip()]
    unknown = [k for k in keys if k not in STYLES]
    if unknown:
        raise SystemExit(f"Unknown styles {unknown}. Available: {list(STYLES)}")
    return keys


def main() -> None:
    ap = argparse.ArgumentParser(description="Phase 0 Fal.ai inpainting spike runner")
    ap.add_argument("--input", required=True, type=Path, help="folder of selfies")
    ap.add_argument("--output", required=True, type=Path, help="output folder")
    ap.add_argument("--styles", default="all", help="'all' or comma list of style keys")
    ap.add_argument("--dry-run", action="store_true", help="no Fal.ai call, no cost")
    ap.add_argument("--watermark", action="store_true", help="apply free-tier watermark")
    args = ap.parse_args()

    style_keys = _parse_styles(args.styles)
    print(
        f"Running {len(style_keys)} style(s) on selfies in {args.input}"
        f"{' [DRY RUN]' if args.dry_run else ''}\n"
    )
    asyncio.run(
        run_spike(
            args.input, args.output, style_keys, dry_run=args.dry_run, watermark=args.watermark
        )
    )


if __name__ == "__main__":
    main()
