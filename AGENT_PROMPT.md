# AGENT_PROMPT.md — Claude Code Kickoff, AI Smile Simulator MVP
> v1.0 | 02.07.2026 | Paste this as the first message to Claude Code, run from repo root.
> Prerequisites: repo contains CLAUDE.md v1.1 and /docs/AI_Smile_Simulator_Architecture_v1.1.docx (or its .md export).

---

## MISSION

Build the AI Smile Simulator MVP codebase, Phases 1–5, exactly per `CLAUDE.md` and Architecture Spec v1.1. Work autonomously in agent loop, but respect the stop points and autonomy boundary below. The goal of this run is **code-complete with mocks**: a fully working local product where every external dependency (inference, auth, payments, email) runs behind a mock flag until real credentials are provided.

Read `CLAUDE.md` fully before writing any code. It is the constitution: tech stack, locked decisions, ML pipeline details (landmarks, prompts, provider interface), UX rules, DB schema, and engineering rules all live there. Do not re-decide anything marked as locked.

## AUTONOMY BOUNDARY

**You do on your own:** all code, tests, migrations, seeds, fixtures, docker-compose, CI config, docs (SETUP.md, BLOCKERS.md, PHASE_REPORT.md), refactors within the plan.

**You NEVER do:** invent credentials, API keys, URLs, accounts, or company data; call paid external APIs; commit secrets; change locked decisions; skip stop points; install telemetry not in the spec.

**Missing secret protocol:** add the variable to `.env.example`, implement the mock path, mark call sites with `TODO(SELENA)`, and add a line to `SETUP.md` explaining exactly what Selena must create and where to put the value. Then continue.

**Blocked protocol:** if an environment problem survives 2 distinct fix attempts, write it to `BLOCKERS.md` (symptom, attempts, hypothesis) and move to the next independent task. Never burn the loop on one blocker.

## VERIFICATION LOOP

After every task: run the relevant checks. After every phase: run `make check` (flutter analyze + flutter test + ruff + mypy + pytest) — must be green before the phase counts as done. Create `make check` in Phase 1 and keep it working forever.

Commits: conventional commits, one logical change each, imperative subject. No secrets, no binaries >1MB, no commented-out code dumps.

---

## PHASE PLAN

### Phase 1 — Skeleton  →  ⛔ STOP POINT 1
Monorepo layout per CLAUDE.md (`/app`, `/backend`, `/supabase`, `/docs`, `/scripts`). Flutter app with all 16 screens stubbed and navigable (routes per Architecture §6), Riverpod wired, RU strings scaffolding. FastAPI skeleton with `/health`, settings via pydantic-settings, structured logging. SQL migrations for all 8 tables (`users, generations, styles, packs, payments, clinics, leads, price_estimates`) + seed: 4 styles with prompt templates, 5 fake Moscow clinics, price_estimates for Moscow/SPb/Tashkent. docker-compose (Postgres + backend). GitHub Actions running `make check`. `.env.example` with every flag: `MOCK_INFERENCE=true, MOCK_AUTH=true, MOCK_PAYMENTS=true, FAL_API_KEY=, SUPABASE_URL=, SUPABASE_ANON_KEY=, SUPABASE_SERVICE_KEY=, YOOKASSA_SHOP_ID=, YOOKASSA_SECRET=, SMTP_URL=, SENTRY_DSN=`.

**DoD:** app boots to Home on emulator and every screen is reachable; `docker compose up` starts backend + DB; migrations apply; seeds load; `make check` green.
**Then STOP.** Write `PHASE_REPORT.md` (built / how to run / what is mocked / questions) and wait for approval.

### Phase 2 — ML Pipeline + Live Pre-Check  →  ⛔ STOP POINT 2
Server: MediaPipe Face Mesh authoritative validation; mouth mask exactly per CLAUDE.md landmark sets (fill outer contour → dilate 15–20px → Gaussian feather σ5–8); prompt construction from style templates; provider abstraction with `MockProvider` (deterministic fixture output: source image + visible teeth-region tint + "MOCK" tag) and `FalProvider` (`fal-ai/flux-pro/v1/fill`, active only when `FAL_API_KEY` set — never call it in this run); pipeline job flow `pending → processing → completed/failed` with cost/duration logging; watermark step (Pillow, semi-transparent diagonal). Client: on-device live pre-check per CLAUDE.md table (face frontal, mouth visible, light, sharpness, distance) with real-time RU hints and gated shutter; gallery uploads run the same checks; `precheck_blocked(reason)` events. End-to-end: upload → styles → generating screen → result with before/after slider, against mock.

**DoD:** full mock generation journey works on emulator; unit tests for mask generation on programmatic fixture faces; pre-check demonstrably blocks dark/blurred/no-face fixtures; `make check` green.
**Then STOP.** `PHASE_REPORT.md`, wait for approval.

### Phase 3 — Monetization
Packs + generation limits (free = 1 with watermark; Mini 149₽/5, Main 499₽/20, Extended 899₽/50). Action-locked paywall: triggers on 2nd generation tap, watermark removal, save — never a timer; multi-page (value → plans). Generation theater on the loading screen: staged messages ("Анализируем улыбку → Подбираем форму → Выравниваем тон") + social proof counter. Cost-estimate block on result: `GET /api/price-estimates?city=&style_id=` from seed data + CTA «Узнать точную цену в клинике рядом». YooKassa integration behind `MOCK_PAYMENTS`: payment creation simulated, but webhook handler is REAL — HMAC signature verification + idempotency table, covered by fixture tests.

**DoD:** mock purchase unlocks a pack; limits enforced server-side; paywall fires only on the three triggers; cost block renders city-correct ranges; webhook tests green.

### Phase 4 — Quality & Hardening
SSIM quality check on non-mask area; retry endpoint; graceful error states in app (failed generation → retry with different photo hint). `/scripts/quality_harness.py`: batch-run N images through the pipeline, output scorecard CSV (the 5 criteria from CLAUDE.md, manual scores entered later). Sentry wiring behind `SENTRY_DSN`. Rate limiting (5 generations/min/user).

**DoD:** harness runs on fixture batch and emits CSV; all error paths render designed states, not crashes; `make check` green.

### Phase 5 — B2B Lead System
Find-clinic screen (seeded clinics, distance-sorted list; map deferred). Lead form (name, phone, preferred_time, consent checkbox «отправить мой результат и контакт выбранной клинике») → `POST /api/leads` → lead row + clinic notification email (SMTP behind env; mock = log to console + save .eml fixture). Branded result delivery: within 1 minute of lead creation the patient gets an email with before/after under the clinic's name/logo («Клиника X получила вашу заявку, вот ваша визуализация») — template with merge fields, mock-rendered to file in dev. Lead status endpoints (`PATCH /api/clinic/leads/:id`), minimal `/api/admin/stats`. Analytics events wired per Architecture §9 including `cost_estimate_viewed`, `branded_result_sent`, `precheck_blocked`.

**DoD:** the full mock journey passes: onboarding → login(mock) → upload(fixture) → style → theater → result+watermark → paywall on 2nd gen → cost block → find clinic → lead form → lead row in DB + both notification artifacts rendered; `make check` green.

### Final deliverables of the run
`SETUP.md` — every manual step for Selena (create Supabase project + push migrations, Fal.ai key, YooKassa shop, SMTP, flip mock flags one by one, smoke-test order). `BLOCKERS.md` — honest log. `PHASE_REPORT.md` per phase. Demo script: 10 steps to show the product to a partner from a cold clone.

---

## WHAT SELENA PREPARES (do not wait for any of this — mock and continue)
GitHub repo access · Supabase project (URL + anon/service keys) · Fal.ai API key · YooKassa test shop · SMTP creds · 20–30 real test selfies (replace programmatic fixtures in Phase 4 harness).

## NORTH STAR
A partner can clone the repo, run two commands, and click through the entire product on an emulator — before a single real API key exists. That is what "done" means for this run.
