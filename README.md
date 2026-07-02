# AI Smile Simulator

Cross-platform mobile app that lets a user upload a selfie, pick a dental style,
and receive an AI-generated visualization of their future smile. The system uses
**inpainting** to modify only the mouth area while preserving the rest of the face
(Architecture **Option 2: Inpainting + FLUX**).

> Visualization only — **not** dental diagnosis, treatment plan, or guarantee.

This repository is the Phase 1 / Phase 2 skeleton described in
`docs/AI_Smile_Simulator_Architecture_v1.0` — a runnable foundation that wires the
three architectural layers together, with clearly marked TODOs where live external
services (Fal.ai, payment providers) plug in.

## Architecture

Three layers (see the architecture spec for the full design):

```
┌─────────────────┐     ┌──────────────────────┐     ┌──────────────────┐
│  Flutter client │────▶│  API Gateway (FastAPI)│────▶│ Fal.ai FLUX Fill │
│   iOS + Android │     │  orchestration + auth │     │   (inference)    │
└─────────────────┘     └──────────┬───────────┘     └──────────────────┘
         │                         │
         │  Supabase Auth (JWT)    │  Supabase: Postgres + Storage + RLS
         └─────────────────────────┴──────────────────────────────────────
```

**Critical constraint:** the generative API is **never** called from the mobile
client. All inference goes through the API Gateway to protect API keys, enforce
generation limits, and log cost.

### ML pipeline (mouth inpainting)

`validate → resize/normalize → MediaPipe Face Mesh → mouth mask → prompt → Fal.ai
FLUX.1 [pro] Fill → quality check → watermark (free tier) → save`

The inference step sits behind a `InferenceProvider` abstraction so Fal.ai can be
swapped for Replicate / self-hosted without touching the pipeline.

## Repository layout

```
backend/          FastAPI orchestration layer (the heart of the system)
  app/
    routers/      generate, packs, styles, clinics, leads, admin, webhooks
    ml/           face mesh, mask generation, prompts, provider abstraction
    services/     Supabase client, storage helpers, notifications
  tests/          pytest suite
supabase/
  migrations/     Postgres schema (8 tables), RLS policies, seed data
app/              Flutter app (16 screens, routes, Riverpod, API client)
scripts/          quality / spike harness (scripts/phase0)
docs/             Architecture spec + partner brief
.github/workflows ci.yml — lint + test
```

## Quick start (mock-first — no keys required)

Everything runs behind mock flags (`MOCK_INFERENCE`, `MOCK_AUTH`, `MOCK_PAYMENTS`,
all default `true`), so a partner can clone and click through the whole product
before a single real credential exists.

```bash
make check          # ruff + pytest (+ flutter analyze if flutter is installed)
```

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env          # defaults are mock-friendly; fill real keys later
uvicorn app.main:app --reload
# OpenAPI docs at http://localhost:8000/docs
```

Run the database migrations against your Supabase project:

```bash
supabase db push          # or apply supabase/migrations/*.sql manually
```

### Flutter app

```bash
cd app
flutter pub get
flutter run            # requires API_BASE_URL + SUPABASE_URL/ANON_KEY via --dart-define
```

See [`SETUP.md`](SETUP.md) for the full manual-setup checklist (real Supabase / Fal.ai
/ YooKassa / SMTP credentials and the order to flip mock flags).

## Configuration decisions (per architecture §13)

| Open question                | Decision taken here                                  |
|------------------------------|------------------------------------------------------|
| API gateway language         | **Python / FastAPI** (best for ML pipeline)          |
| Face detection location      | **Server-side** (more control, protects pipeline)    |
| Photo upload                 | **Direct to Supabase** via signed URL (less API load)|
| Generation status            | **Client polling** `GET /generate/:id` (simpler MVP) |
| Checkout                     | **Web checkout first** (YooKassa) to avoid 30% tax   |
| Clinic notification          | **Email** for MVP, WhatsApp in Phase 2               |

## Status

This is a **skeleton**: structure, schema, wiring, and runnable stubs. Items marked
`# TODO(phase-N)` require live credentials or external approvals (Fal.ai key,
YooKassa merchant, WhatsApp Business API) and are not wired to real services yet.
