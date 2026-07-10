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

A dedicated project URL is configured as `htclwrotnmhtbrdisqcu`
(`https://htclwrotnmhtbrdisqcu.supabase.co`). Do not assume its migration state:
verify and apply numbered migrations `0001` through `0010` in order before deploy.

Put these in `backend/.env` (copy from `.env.example`):

- `SUPABASE_URL` — Project Settings → API → Project URL
- `SUPABASE_SECRET_KEY` — current server key (SECRET, bypasses RLS, backend only)
- `SUPABASE_PUBLISHABLE_KEY` — public key for Flutter/web clients
- `SUPABASE_JWT_SECRET` — legacy HS256 fallback only; current ES256/RS256 user tokens
  are verified against the project's public JWKS endpoint

`SUPABASE_SERVICE_ROLE_KEY` and `SUPABASE_ANON_KEY` remain temporary legacy aliases.
Prefer the current secret/publishable keys and deactivate legacy keys after every
deployed client and backend has migrated.

To recreate from scratch elsewhere, apply `supabase/migrations/*.sql` in order.
Never apply `supabase/seed_dev.sql` to production: those clinic names and contacts are
test fixtures. Insert only approved pilot clinics with confirmed notification contacts.

For production, also set a random `ADMIN_API_KEY` of at least 32 characters and an
explicit comma-separated `CORS_ALLOWED_ORIGINS`. Startup fails if production uses
any mock service, a default admin key, missing required service keys, or wildcard CORS.

For real Flutter phone OTP:

1. Enable Phone Auth in Supabase and configure a supported SMS provider.
2. Review Auth rate limits and CAPTCHA before inviting beta users.
3. Run/build the app with the public project values:

```bash
flutter run \
  --dart-define=SUPABASE_URL=https://htclwrotnmhtbrdisqcu.supabase.co \
  --dart-define=SUPABASE_PUBLISHABLE_KEY=<public-key> \
  --dart-define=API_BASE_URL=<railway-api>/v1
```

When no Supabase values are compiled in, the local-only mock OTP is `000000` and
the API client sends `mock-dev-token`. A production build must include the real
public values; the backend independently rejects mock auth in production.

Migration `0009_photo_retention.sql` makes photo deletion retryable. After it is
applied, configure a daily Railway cron using the same backend image:

```bash
python -m app.jobs.retention --limit 100
```

Run `python -m app.jobs.retention --dry-run --limit 100` first. The live command
removes original/result/mask objects through the Storage API, then clears their paths
and records `photo_deleted_at`. A failed delete stays pending for the next run.

## 2. Fal.ai (inference) — pay per use ($0.05/MP, rounded up per image)

1. Create a key at https://fal.ai/dashboard/keys
2. `backend/.env`: `FAL_API_KEY=...` and set `MOCK_INFERENCE=false`
3. Smoke test: run a generation; `/health` should report `"inference_provider":"fal_flux_pro_fill"`.

At the current published rate, 1024x1024 is slightly above 1 MP and is billed as
2 MP, so the repository estimates $0.10 per generation. Verify actual dashboard
charges; vendor pricing can change.

> NOTE: this repo's cloud env blocks outbound to `fal.run` (egress policy). Run the
> Phase 0 spike locally (see `scripts/phase0/README.md`).

## 2.1 Railway backend

1. Create an isolated service from `parkourcafe/SMILE-simulator`.
2. Set **Root Directory** to `/backend` and **Config file path** to
   `/backend/railway.json`.
3. Create a `staging` environment first. Use `APP_ENV=staging` while mocks remain.
4. Add variables from `backend/.env.example`; never paste secrets into GitHub files.
5. Generate a Railway domain and verify both `/health` and `/ready`.
6. Run the retention command as a separate daily cron service only after migration
   `0009_photo_retention.sql` is applied.

The image binds to Railway's injected `PORT`, runs as a non-root user, installs the
ML dependencies, and includes the pinned Face Landmarker bundle with a verified
SHA-256 checksum. `APP_ENV=production` refuses to start with any mock service, a
missing/changed model, missing Supabase/Fal.ai/YooKassa credentials, default admin
key, unsafe CORS, or no clinic notification channel.

Promotion to production is allowed only after migrations `0008`–`0010`, Phase 0 GO,
real OTP, one approved clinic, legal publication, and staging smoke tests. Roll back
by selecting the previous successful Railway deployment; rotate any credential that
appeared in logs or was shared outside the Railway secret store.

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
