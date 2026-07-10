# Phase 0 - standardized Fal.ai spike checklist

> Created: 28.06.2026 | 03:38 | Bali
> Updated: 10.07.2026 | 19:48 | Bali
> Purpose: decide whether the fixed ZubiLook mouth-inpainting pipeline is ready for a
> closed beta. This is product-quality evidence, not clinical evidence.

## 1. Freeze the evaluation set

- [ ] Exactly 10 consented selfies, selected before generation.
- [ ] Pseudonymous filenames with no name, phone, email, or clinic identifier.
- [ ] Deliberate variation in lighting, skin tone, face shape, visible teeth, camera
      quality, and minor pose while remaining usable frontal smile photos.
- [ ] Exact duplicates removed.
- [ ] `consent_manifest.csv` has one matching row per image, a consent version,
      consent date, and deletion date no later than 30 days.
- [ ] Intentionally unusable photos are stored as a separate diagnostic set and do
      not enter the 10-image quality score.

## 2. Freeze the pipeline

- [ ] Source commit recorded in `run_config.json`.
- [ ] Real MediaPipe Face Landmarker model checksum equals
      `64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff`.
- [ ] One style only: `natural_white` for the first standardized run.
- [ ] One prompt/configuration for all 10 people; no person-specific retries or edits.
- [ ] No watermark in the quality run.
- [ ] `FAL_API_KEY` exists only in the local environment, never in files or logs.

## 3. Execute

```bash
export FAL_API_KEY=...
python scripts/phase0/run_spike.py \
  --input ~/phase0_selfies \
  --output ~/phase0_run_v1 \
  --styles natural_white
```

- [ ] Preflight reports 10 images and zero approximate masks.
- [ ] `input_manifest.csv` and `run_config.json` are written before inference.
- [ ] `results.csv` records status, provider request ID, latency, estimated cost,
      input/output/mask/prompt checksums, and errors for every attempt.
- [ ] Compare estimated cost with the actual Fal.ai account charge. Fal.ai currently
      quotes $0.05/MP rounded up to a whole megapixel, so 1024x1024 is estimated at
      $0.10 per generation.

## 4. Score before aggregation

Rate each successful pair from 1 (fail) to 5 (excellent):

| Criterion | 1 = fail | 5 = excellent |
|---|---|---|
| Tooth realism | plastic or structurally implausible | natural-looking teeth |
| Face preservation | identity, lips, skin, or lighting changed | no unintended change |
| Boundary blending | visible pasted edge | seamless transition |
| Style accuracy | requested effect is absent | requested effect is clear |
| Emotional response | uncanny or uncomfortable | worth sharing with a friend |

- [ ] Reviewers fill every cell in `scorecard.csv` before viewing averages.
- [ ] Repeated identity/face-preservation failures are marked explicitly.
- [ ] A dentist may comment on realism, but the report does not claim clinical
      validation or guaranteed treatment results.

## 5. Generate the decision

```bash
python scripts/phase0/evaluate_scorecard.py \
  --results ~/phase0_run_v1/results.csv \
  --scorecard ~/phase0_run_v1/scorecard.csv \
  --output ~/phase0_run_v1/PHASE0_REPORT.md
```

| Decision | Fixed rule | Next action |
|---|---|---|
| GO | 10/10 succeed, one style, overall >=3.5, every criterion average >=2.0, no recurring identity failure | Proceed to closed-beta infrastructure smoke. |
| ITERATE | Overall 3.0-3.49, a criterion below 2.0, any failed generation, or non-standard evidence | Make one versioned mask/prompt change and rerun the same gate. |
| NO-GO | Overall below 3.0 or recurring identity/face-preservation failure | Stop production inference promotion and revisit the pipeline. |

Borderline values are not rounded up. Style-range demos and diagnostic bad-photo
tests happen after this fixed gate and cannot replace it.

## 6. Close the data set

- [ ] Preserve the private report/checksums needed for the decision record.
- [ ] Do not publish identifiable before/after pairs without separate publication
      consent.
- [ ] Delete every input and generated image by its recorded `deletion_due_at` date.
- [ ] Record deletion completion without retaining the deleted images.
