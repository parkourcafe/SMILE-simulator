# Phase 0 evidence runner

> Updated: 10.07.2026 | 19:48 | Bali

This runner produces the auditable evidence for the fixed ZubiLook Phase 0 quality
gate. A dry-run checks the harness only and can never support a GO decision.

## 1. Prepare the runtime

```bash
cd backend
pip install -e ".[ml]"
mkdir -p .cache
curl -L -o .cache/face_landmarker.task \
  https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
shasum -a 256 .cache/face_landmarker.task
# Expected: 64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff
```

The valid run must use real CPU Face Landmarker output. Approximate masks abort
preflight before any paid Fal.ai call.

## 2. Prepare exactly 10 inputs

- Use pseudonymous filenames such as `selfie_01.jpg`; do not put names or phone
  numbers in filenames.
- Put exactly 10 evaluation images in one folder. Keep deliberately bad diagnostic
  images in a different folder and do not mix them into the quality gate.
- Copy `consent_manifest_template.csv` to `consent_manifest.csv`, add one row per
  image, and record consent version/date plus a deletion date no later than 30 days.
- Do not commit the images, manifests, results, or reports.

## 3. Run the fixed test

```bash
export FAL_API_KEY=...
python scripts/phase0/run_spike.py \
  --input ~/phase0_selfies \
  --output ~/phase0_run_2026-07-10_v1 \
  --styles natural_white
```

Fal.ai currently bills FLUX.1 [pro] Fill at $0.05 per megapixel rounded up to the
next whole megapixel. A 1024x1024 generation is therefore estimated at $0.10; verify
the actual account charge after the run. Official endpoint schema:
https://fal.ai/models/fal-ai/flux-pro/v1/fill/api

For a credential-free harness smoke with any input count:

```bash
python scripts/phase0/run_spike.py \
  --input ./synthetic_selfies \
  --output /tmp/zubilook_phase0_dry \
  --dry-run --allow-nonstandard-count --styles all
```

## 4. Score and decide

Review every `*__compare.png` without tuning prompts per person. Fill all five
ratings in `scorecard.csv`, then freeze the scores before looking at aggregates:

```bash
python scripts/phase0/evaluate_scorecard.py \
  --results ~/phase0_run_2026-07-10_v1/results.csv \
  --scorecard ~/phase0_run_2026-07-10_v1/scorecard.csv \
  --output ~/phase0_run_2026-07-10_v1/PHASE0_REPORT.md
```

Use `--recurring-identity-failure` when reviewers confirm a repeated change to the
person outside the requested smile area; this forces NO-GO.

Outputs include `input_manifest.csv`, `run_config.json`, `results.csv` with provider
request IDs and checksums, generated/compare images, `scorecard.csv`, `summary.txt`,
and the final report. Delete the private input/output set by every recorded
`deletion_due_at` date.
