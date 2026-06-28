# Phase 0 spike runner

Batch-tests mouth inpainting on real selfies using the production pipeline.
Full procedure and go/no-go criteria: [`docs/Phase0_Spike_Checklist.md`](../../../docs/Phase0_Spike_Checklist.md).

```bash
cd api-gateway
pip install -e ".[ml]"          # real MediaPipe landmarks (required for a valid spike)
export FAL_API_KEY=...
cd scripts/phase0
python run_spike.py --input ./selfies --output ./out --styles all
```

| flag | meaning |
|---|---|
| `--input DIR` | folder of selfies (jpg/png/webp/heic) |
| `--output DIR` | where results + CSVs are written |
| `--styles` | `all` or comma list: `natural_white,straight_smile,veneer_effect,hollywood_smile` |
| `--dry-run` | skip Fal.ai (no key, no cost) — for testing the script only |
| `--watermark` | apply the free-tier watermark |

Outputs: `*__compare.png` (before/after), `results.csv`, `scorecard.csv` (fill by hand),
`summary.txt`. Styles live in `styles.py` (mirror of migration `0003_seed_styles.sql`).
