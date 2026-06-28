# Phase 0 — Spike Test Checklist (10 selfies on Fal.ai)

> Created: 28.06.2026 | 03:38 | Bali
> Goal: prove FLUX.1 [pro] Fill produces trustworthy mouth-inpainting on real selfies
> BEFORE writing more product code. Output is a scored demo-pack + a go/no-go call.
> Scope: this is the only Phase-0 deliverable. No app, no payments, no clinics yet.

---

## 0. Two ways to run the spike

**A. Web playground (manual, zero setup).** Upload image + a hand-drawn mouth mask +
prompt to the Fal.ai `fal-ai/flux-pro/v1/fill` playground. Fastest to eyeball, but the
mask is not the one we ship.

**B. Batch runner (recommended).** `api-gateway/scripts/phase0/run_spike.py` runs each
selfie through the **same pipeline as the MVP** (auto mouth mask + our prompts +
provider abstraction), so the result predicts production quality, and it auto-builds
the before/after pairs + scorecard. Prefer B; use A only for quick spot checks.

```bash
cd api-gateway
pip install -e ".[ml]"                 # MediaPipe + OpenCV for REAL mouth landmarks
export FAL_API_KEY=...                  # from fal.ai dashboard
cd scripts/phase0
python run_spike.py --input ./selfies --output ./out --styles all

# offline sanity check (no key, no cost, approximate mask):
python run_spike.py --input ./selfies --output ./out --dry-run
```

> ⚠️ Without the `ml` extra installed, the mask falls back to an APPROXIMATE region and
> `face_approximate=True` in `results.csv` — fine for testing the script, **not** valid
> for quality judgement. Install `.[ml]` for the real spike.

Outputs in `out/`: `*__compare.png` (before/after), `results.csv` (cost/latency/heuristic),
`scorecard.csv` (fill this in by hand), `summary.txt`.

---

## 1. Collect the selfies (do this first)

- [ ] **10 selfies minimum.** Diverse on purpose: 5 women + 5 men, ages 20–55,
      different skin tones, different tooth conditions (yellow, crooked, gaps, missing,
      healthy). — *Partner Brief §17.1*
- [ ] Frontal, mouth slightly open, decent lighting (matches the app's camera hint).
- [ ] Also collect **3–5 deliberately bad** photos (dark, side angle, mouth closed) to
      document failure modes honestly. Honesty builds trust with technical partners.
- [ ] Consent to use each photo internally (152-ФЗ habit from day one).

## 2. Run the spike

- [ ] Run the batch runner over all 10 with `--styles all` (4 styles × 10 = 40 results).
- [ ] Confirm `results.csv` has no unexpected `error` rows (no_face / multiple_faces /
      too_small are expected on the bad set — note them).
- [ ] Record from `summary.txt`: success rate, total cost, **effective cost per good
      generation** (the number partners care about).

## 3. Score the results (the actual point)

Rate every good before/after pair on the **5 criteria**, scale 1 (fail) → 5 (excellent).
*Source: CLAUDE.md → Quality Criteria / Partner Brief §17.2.*

| # | Criterion | 1 = Fail | 5 = Excellent |
|---|---|---|---|
| 1 | Tooth realism | plastic, fake teeth | indistinguishable from real |
| 2 | Face preservation | lips/skin/lighting changed | zero change outside mouth |
| 3 | Boundary blending | visible "pasted-in" edge | seamless mask transition |
| 4 | Style accuracy | styles look identical | clear difference per style |
| 5 | Emotional response | uncanny / uncomfortable | "wow, I'd show a friend" |

- [ ] Fill `scorecard.csv` (one row per pair). Compute `avg` per row.
- [ ] Criterion #5 (emotional response) is the tie-breaker — a warm imperfect result
      beats a cold perfect one.

## 4. Who evaluates (*Partner Brief §17.3*)

- [ ] Internal team rates all pairs; compute the overall average.
- [ ] 3–5 outsiders (friends/family), shown pairs with no context: "would you pay ₽149
      to get this for yourself?"
- [ ] 1 dentist/orthodontist if available — tooth-shape realism + clinical plausibility.

## 5. Assemble the demo-pack (*Partner Brief §17.1*)

- [ ] 10 before/after pairs (the `*__compare.png` files).
- [ ] 3–4 style variations shown for 3 subjects (range demo).
- [ ] 3–5 honest failure examples.
- [ ] Quality scorecard (the filled `scorecard.csv`, summarized as one table).
- [ ] Cost data: API cost/gen, avg attempts per good result, effective cost/good (from
      `summary.txt`).
- [ ] 30-second raw screen recording of the flow (do once the app skeleton runs).

## 6. Go / No-Go decision (*Partner Brief §17.4 / CLAUDE.md*)

| Outcome | Threshold | Action |
|---|---|---|
| ✅ GO | avg ≥ 3.5, no criterion < 2.0 | Proceed to closed beta; show demo-pack to first 5 clinics. |
| ⚠️ CONDITIONAL | avg 3.0–3.4 | Iterate mask/prompts/params; retest in 1 week. |
| ❌ NO-GO | avg < 3.0 OR 3+ criteria < 2.0 | Pipeline needs fundamental changes. |

## 7. If iterating (cheapest levers first)

1. Mask: tune `DILATE_PX` (15–20) and `FEATHER_SIGMA` (5–8) in `app/ml/mask.py`.
2. Prompt: edit per-style templates in `scripts/phase0/styles.py`; keep a version log
   and A/B test (architecture §5.2).
3. Inference: `num_inference_steps` / `guidance_scale` in `ProviderConfig`.
4. Only after the above plateau, consider the Phase-2 LoRA path (locked: not now).

---

**Definition of done for Phase 0:** filled `scorecard.csv`, a one-page cost summary, the
demo-pack assembled, and a written GO / CONDITIONAL / NO-GO with the average score.
