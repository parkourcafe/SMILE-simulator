# PHASE_REPORT.md — AI Smile Simulator

> Status of the v1.1 reconciliation run (structure + 4 conversion features + mocks).
> Date: 02.07.2026 | Bali.

## What this run did

Reconciled the existing MVP codebase with **CLAUDE.md v1.1 + AGENT_PROMPT.md**:
adopted the v1.1 repo layout, made the whole product run mock-first (zero
credentials), and built the four v1.1 conversion features.

## Built

### Structure (v1.1 layout)
- `api-gateway/ → backend/`, `mobile/ → app/`, spike moved to top-level `scripts/phase0/`.
- Updated all path refs (CI, pyproject, tests, docs, .gitignore). `make check` added.

### Mock-first (North Star: clone + run + click through, no keys)
- `MOCK_INFERENCE` / `MOCK_AUTH` / `MOCK_PAYMENTS` — default **true**.
- `MockProvider`: deterministic offline inpaint (whitens mouth + MOCK tag), no cost.
- Provider registry routes to mock when the flag is on or `FAL_API_KEY` is absent.
- `MOCK_AUTH`: `Bearer mock-dev-token` / empty header → dev user.
- `MOCK_PAYMENTS`: purchase auto-succeeds + activates pack; **webhook stays real**
  (HMAC verify + idempotency, fixture-tested).
- `/health` reports effective provider + mock state.

### v1.1 conversion features
1. **Live photo pre-check** (app): 5 checks (face/mouth/light/sharpness/distance) +
   RU hints + gated Continue + `precheck_blocked`; pluggable `FaceProbe`
   (advisory default; real MediaPipe/camera = documented native TODO).
2. **Generation theater** (app): staged RU messages + social proof, not a spinner.
3. **Action-locked paywall** (app): fires only on 2nd-gen attempt / watermark
   removal / save — never a timer. Multi-page (value → plans). Real purchase wiring.
4. **Cost-estimate anchor** (backend + app): 8th table `price_estimates`
   (city × style × treatment × range × currency, Moscow/SPb RUB, Tashkent UZS) +
   `GET /v1/api/price-estimates` + result-screen block + "clinic nearby" CTA.
5. **Branded result delivery** (backend): patient gets before/after under the chosen
   clinic's brand; SMTP email or dev artifact file; `branded_result_sent` logged.

### Analytics contract
- Client facade (Mixpanel TODO): `cost_estimate_viewed`, `precheck_blocked`
  (`branded_result_sent` logged server-side).

## How to run

```bash
make check                         # ruff + pytest (30) [+ flutter analyze in CI]
cd backend && pip install -e ".[dev]" && uvicorn app.main:app --reload
# http://localhost:8000/health  → mocks all true, provider "mock"
```
Flutter: `cd app && flutter pub get && flutter run`. Full setup: `SETUP.md`.

## What is mocked (and how to make it real)
Inference (Fal.ai), auth (Supabase JWT), payments (YooKassa), email (SMTP),
analytics (Mixpanel). Flip one flag at a time — see `SETUP.md`.

## Verified
- 30 backend tests green; ruff lint + format clean (backend + scripts).
- End-to-end mock generation produces a valid result PNG with **zero** keys/network.
- `price_estimates` applied to Supabase `htclwrotnmhtbrdisqcu` (4 rows × 3 cities).

## NOT done / open (see BLOCKERS.md)
- `flutter analyze` not run in this env (no toolchain) — CI covers it; Dart by review.
- Real on-device MediaPipe pre-check (needs camera + mlkit plugins) — advisory stub.
- Fal.ai spike must run locally (cloud egress blocks `fal.run`).
- Direct-Postgres adapter (app data layer is PostgREST/Supabase-only today).

## Open questions for Selena
1. Price-estimate ranges are **team estimates** — replace with clinic-sourced numbers
   before any partner-facing use?
2. Pre-check: which plugin for on-device detection (google_mlkit vs MediaPipe Flutter)?
3. Keep the hosted Supabase as the single datastore, or add local Postgres parity?
