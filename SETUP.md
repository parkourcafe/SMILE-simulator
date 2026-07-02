# SETUP.md — what Selena must do manually

> Everything below is EXTERNAL setup Claude Code cannot do (accounts, keys, money).
> The app is **mock-first**: it runs end-to-end with zero credentials. Fill these in
> only to swap a mock for the real service, one flag at a time.

## 0. Run it right now (no credentials)

```bash
make check          # ruff + pytest (+ flutter analyze if flutter installed)
cd backend && pip install -e ".[dev]" && uvicorn app.main:app --reload
# open http://localhost:8000/health  -> "inference_provider":"mock", mocks all true
```

The full generation journey (upload → style → theater → result with watermark)
works on mocks. Data-backed screens (styles, clinics, price estimates, leads)
need Supabase — see step 1.

## 1. Supabase (datastore) — free tier

A dedicated project is already provisioned: `htclwrotnmhtbrdisqcu`
(`https://htclwrotnmhtbrdisqcu.supabase.co`). All 8 tables + seeds are applied.

Put these in `backend/.env` (copy from `.env.example`):

- `SUPABASE_URL` — Project Settings → API → Project URL
- `SUPABASE_SERVICE_ROLE_KEY` — Project Settings → API → service_role key (SECRET — server only)
- `SUPABASE_JWT_SECRET` — Project Settings → API → JWT Secret (only needed when `MOCK_AUTH=false`)
- `SUPABASE_ANON_KEY` — for the Flutter app (`--dart-define SUPABASE_ANON_KEY=...`)

To recreate from scratch elsewhere: apply `supabase/migrations/*.sql` in order,
then `supabase/seed_dev.sql` (10 test clinics). `auth.users` is Supabase-provided.

## 2. Fal.ai (inference) — pay per use (~$0.05/MP)

1. Create a key at https://fal.ai/dashboard/keys
2. `backend/.env`: `FAL_API_KEY=...` and set `MOCK_INFERENCE=false`
3. Smoke test: run a generation; `/health` should report `"inference_provider":"fal_flux_pro_fill"`.

> NOTE: this repo's cloud env blocks outbound to `fal.run` (egress policy). Run the
> Phase 0 spike locally (see `scripts/phase0/README.md`).

## 3. YooKassa (payments RU)

1. Create a test shop → get `YOOKASSA_SHOP_ID` + `YOOKASSA_SECRET_KEY`.
2. `backend/.env`: fill both, set `MOCK_PAYMENTS=false`.
3. Configure the webhook URL → `POST {API_BASE_URL}/v1/api/webhooks/yookassa`.
   The webhook handler (HMAC verify + idempotency) is REAL even in mock mode.

## 4. SMTP (clinic + branded patient email)

Fill `SMTP_HOST/PORT/USER/PASSWORD/FROM`. Without SMTP:
- clinic notifications are logged (never fail the lead);
- branded patient result is rendered to `backend/.artifacts/branded/<lead_id>.html`.

## 5. WhatsApp Business API (preferred clinic channel) — optional

Fill `WHATSAPP_TOKEN` + `WHATSAPP_PHONE_ID`. Preferred over email when set.

## 6. Analytics / errors — optional

- `SENTRY_DSN` — error tracking (backend + Flutter).
- Mixpanel — client analytics; token wiring is a `TODO(SELENA)` in `app/lib/src/services/analytics.dart`.

## Flip order (recommended)

1. Supabase (unlocks all data screens) →
2. Fal.ai (real generations, run locally) →
3. SMTP (real lead + branded email) →
4. YooKassa (real payments) →
5. WhatsApp, Sentry, Mixpanel.

Flip one flag, smoke-test, commit. Never commit `.env` (it is gitignored).
