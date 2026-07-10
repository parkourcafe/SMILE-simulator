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
verify and apply numbered migrations `0001` through `0014` in order before deploy.
Do not skip `0011_auth_user_provisioning.sql` or
`0012_photo_processing_consent.sql`; `0013_atomic_generation_quota.sql` is required
before deploying the backend version that calls the reservation RPC. Migration
`0014_yookassa_payments.sql` is required before enabling real pack checkout.

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

Migration `0011_auth_user_provisioning.sql` backfills existing Auth users and keeps
`public.users` synchronized after phone/email changes. Verify after a real OTP signup
that the same UUID exists in both `auth.users` and `public.users` before testing quota.

Migration `0012_photo_processing_consent.sql` creates server-issued, per-photo consent
receipts. The app records a receipt through the authenticated API before it receives
the private Storage path; generation rejects a receipt owned by another user, an old
consent version, or a different path. The same migration replaces the broad owner-write
Storage policy: authenticated clients can upload/update only the original object named
by a current receipt; backend service credentials remain responsible for results,
masks, and deletion.

Before applying `0013_atomic_generation_quota.sql`, this preflight must return zero
rows. Do not silently rewrite inconsistent production counters:

```sql
select 'users' as source, id from users where free_gens_used < 0
union all
select 'packs', id from packs
where generations_total <= 0
   or generations_used < 0
   or generations_used > generations_total
union all
select 'active_generations', id from generations
where status in ('pending', 'processing');
```

Migration `0013` reserves the free or pack credit and inserts the generation in one
transaction. It ignores expired packs, enforces the per-user generation rate limit,
marks successful reservations consumed, and returns a credit exactly once when a
generation becomes failed or deleted. Apply it in a short maintenance window before
deploying the matching backend so old and new quota paths cannot run concurrently.

Migration `0009_photo_retention.sql` makes photo deletion retryable. After it is
applied, configure a daily Railway cron using the same backend image:

```bash
python -m app.jobs.retention --limit 100
```

Run `python -m app.jobs.retention --dry-run --limit 100` first. The live command
removes original/result/mask objects through the Storage API, then clears their paths
and records `photo_deleted_at`. A failed delete stays pending for the next run.

Also configure a Railway cron every five minutes for reservations left by a crashed
worker. Run the dry-run once before enabling the live command:

```bash
python -m app.jobs.quota_reconciliation --dry-run --limit 100
python -m app.jobs.quota_reconciliation --limit 100
```

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
7. Run quota reconciliation as a separate five-minute cron only after migration
   `0013_atomic_generation_quota.sql` is applied.

The image binds to Railway's injected `PORT`, runs as a non-root user, installs the
ML dependencies, and includes the pinned Face Landmarker bundle with a verified
SHA-256 checksum. Uvicorn access logs are disabled; the app emits JSON request logs
with `X-Request-ID` and never logs query strings, request bodies, IP addresses, or
raw exception values. `MAX_REQUEST_BODY_BYTES` defaults to `262144` because clients
upload photos directly to private Storage; the API accepts only small JSON commands.
The gateway retries idempotent external GET requests at most three times on transport,
`408`, `425`, `429`, and selected `5xx` failures. It never automatically retries
payment creation, inference submission, notifications, or other writes.
`APP_ENV=production` refuses to start with any mock service, a
missing/changed model, missing Supabase/Fal.ai/YooKassa/Sentry credentials, default
admin key, unsafe CORS, or no clinic notification channel.

Promotion to production is allowed only after migrations `0008`–`0014`, Phase 0 GO,
real OTP, one approved clinic, legal publication, and staging smoke tests. Roll back
by selecting the previous successful Railway deployment; rotate any credential that
appeared in logs or was shared outside the Railway secret store.

## 3. YooKassa (payments RU)

1. Create a test shop → get `YOOKASSA_SHOP_ID` + `YOOKASSA_SECRET_KEY`.
2. Set `YOOKASSA_RETURN_URL` to a public HTTPS page controlled by ZubiLook.
3. Apply `0014_yookassa_payments.sql`, then fill the credentials and set
   `MOCK_PAYMENTS=false` in Railway staging.
4. In the YooKassa dashboard, subscribe the public HTTPS endpoint
   `POST {API_BASE_URL}/v1/api/webhooks/yookassa` to `payment.succeeded` and
   `payment.canceled`.
5. Create one test payment. Verify redirect, pending local row, server-to-server GET
   verification, exactly one completed payment, and exactly one linked pack after the
   webhook. Replay the same notification and confirm no second pack is created.
6. Confirm the shop's receipt/fiscalization settings with the merchant's accountant or
   payment specialist before real charges; do not infer that requirement from test mode.

The implementation follows YooKassa's official server-side redirect flow with HTTP
Basic Auth and `Idempotence-Key`. Incoming notifications are not trusted directly:
the backend retrieves the current payment object from YooKassa and matches payment ID,
status, paid flag, amount, currency, user, and pack metadata before atomic activation.

Official references:

- https://yookassa.ru/developers/payment-acceptance/getting-started/quick-start
- https://yookassa.ru/developers/using-api/webhooks
- https://yookassa.ru/developers/using-api/response-handling/recommendations

## 4. SMTP (clinic + branded patient email)

Fill `SMTP_HOST/PORT/USER/PASSWORD/FROM`. Without SMTP:
- clinic notifications are logged (never fail the lead);
- branded patient result is rendered to `backend/.artifacts/branded/<lead_id>.html`.

## 5. WhatsApp Business API (preferred clinic channel) — optional

Fill `WHATSAPP_TOKEN` + `WHATSAPP_PHONE_ID`. Preferred over email when set.

## 6. Analytics / errors

- `SENTRY_DSN` — required for backend production, optional in local/staging. Create the
  project in the processor region approved for the published privacy policy. Backend
  reporting disables default PII, request bodies, breadcrumbs, local variables, and
  tracing; a final scrubber also removes identities, headers, query strings, exception
  values, and frame variables. Verify one synthetic staging exception before promotion.
- Mixpanel — client analytics; token wiring is a `TODO(SELENA)` in `app/lib/src/services/analytics.dart`.

## Flip order (recommended)

1. Supabase (unlocks all data screens) →
2. Fal.ai (real generations, run locally) →
3. SMTP (real lead + branded email) →
4. YooKassa (real payments) →
5. Sentry →
6. WhatsApp, Mixpanel.

Flip one flag, smoke-test, commit. Never commit `.env` (it is gitignored).
