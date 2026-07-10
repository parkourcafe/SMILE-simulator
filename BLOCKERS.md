# BLOCKERS.md — honest log of environment blockers

Format: symptom → attempts → hypothesis → status.

## 1. Outbound to Fal.ai blocked in the cloud env (Phase 0)
- **Symptom:** `run_spike.py` → every generation `ProxyError: 403 Forbidden`;
  proxy status shows `connect_rejected` for `fal.run:443`.
- **Attempts:** verified `FAL_API_KEY` is valid; checked `$HTTPS_PROXY/__agentproxy/status`.
- **Hypothesis:** org egress policy for this session does not allow `fal.run`
  (documented behaviour — do not route around it).
- **Status:** OPEN (infra). Workaround: run the Phase 0 spike **locally**
  (`scripts/phase0/README.md`). Does not affect the app — inference is mocked by default.

## 2. No Flutter toolchain in the build env
- **Symptom:** `flutter`/`dart` not installed; can't run `flutter analyze`/`flutter test` here.
- **Attempts:** `which flutter dart` → not found.
- **Hypothesis:** image ships backend tooling only.
- **Status:** OPEN (infra). Mitigation: `make check` skips analyze gracefully when
  flutter is absent; **CI runs `flutter analyze`** on every push. Dart written by review.

## 3. Live on-device pre-check needs heavy native plugins
- **Symptom:** real MediaPipe/face-mesh over a camera preview stream requires the
  `camera` + `google_mlkit_face_detection` (or a MediaPipe Flutter) plugins, which
  aren't in `pubspec.yaml` and can't be compiled/verified in this env.
- **Decision:** implemented the pre-check **contract** (5 checks + RU hints + gated
  Continue + `precheck_blocked` events) with a pluggable `FaceProbe`; the default
  `AdvisoryFaceProbe` passes so the mock journey isn't blocked. Server validation
  stays authoritative.
- **Status:** OPEN (product/dep decision for Selena/dev) — wire a real probe +
  camera-stream preview when adding those plugins.

## 4. Supabase MCP flakiness during migration apply
- **Symptom:** intermittent "Tool permission stream closed" / MCP disconnects while
  applying migrations.
- **Attempts:** re-checked table state with `list_tables` before retrying to avoid
  double-apply; retried apply — succeeded.
- **Status:** RESOLVED (migrations 0006/0007 applied; verified 4 rows × 3 cities).

## 5. App data layer is PostgREST-only (docker-compose Postgres not wired)
- **Symptom:** migrations reference `auth.users` (Supabase), so they can't auto-apply
  to a plain local Postgres; the app reads via Supabase REST, not raw Postgres.
- **Status:** KNOWN LIMITATION. `docker compose up backend` runs the mock journey;
  data-backed screens point at the hosted Supabase project (or `supabase start`).
  A direct-Postgres adapter is future work.

## 6. Supabase connector and production keys are not available in this session
- **Symptom:** remote migration history, grants, and form rows cannot be inspected;
  no public/publishable or server key is present in the current environment.
- **Impact:** migrations `0008`–`0014`, website forms, Auth profile provisioning,
  photo consent, quota, and payment activation cannot be marked production-ready.
- **Status:** OPEN (external). Selena will reconnect the Supabase connector; then apply
  migrations in order and run the positive and negative smoke checks from the handoff.

## 7. Sentry project, DSN, and approved processing region are not available
- **Symptom:** the privacy-safe backend integration is implemented, but there is no
  real staging/production DSN and the processor region is not confirmed for legal text.
- **Impact:** alert delivery and one synthetic staging exception cannot be verified;
  `APP_ENV=production` intentionally refuses to start without `SENTRY_DSN`.
- **Status:** OPEN (external). Create the Sentry project only after choosing the region,
  store its DSN in Railway secrets, then run the smoke procedure from `SETUP.md`.
