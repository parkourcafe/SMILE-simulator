# Phase 0 spike runner

Batch-tests mouth inpainting on real selfies using the production pipeline.
Full procedure and go/no-go criteria: [`docs/Phase0_Spike_Checklist.md`](../../docs/Phase0_Spike_Checklist.md).

```bash
cd backend
pip install -e ".[ml]"          # real MediaPipe landmarks (required for a valid spike)

# MediaPipe Tasks needs a model bundle + OpenGL system libs:
mkdir -p .cache
curl -L -o .cache/face_landmarker.task \
  https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
# Debian/Ubuntu: apt-get install -y libgles2 libegl1 libgl1

export FAL_API_KEY=...
cd ../scripts/phase0
python run_spike.py --input ./selfies --output ./out --styles all
```

> Without the model bundle (or the `ml` extra), detection falls back to an
> APPROXIMATE mouth region (`face_approximate=True` in results.csv) — fine for
> smoke-testing the script, not valid for quality judgement.

| flag | meaning |
|---|---|
| `--input DIR` | folder of selfies (jpg/png/webp/heic) |
| `--output DIR` | where results + CSVs are written |
| `--styles` | `all` or comma list: `natural_white,straight_smile,veneer_effect,hollywood_smile` |
| `--dry-run` | skip Fal.ai (no key, no cost) — for testing the script only |
| `--watermark` | apply the free-tier watermark |

Outputs: `*__compare.png` (before/after), `results.csv`, `scorecard.csv` (fill by hand),
`summary.txt`. Styles live in `styles.py` (mirror of migration `0003_seed_styles.sql`).
