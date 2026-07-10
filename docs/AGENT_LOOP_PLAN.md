# ZubiLook agent-loop release plan

> Created: 10.07.2026 | 14:29 | Bali  
> Owner: Selena + Codex  
> Status: ACTIVE  
> Scope: website intake -> Phase 0 -> production backend/app -> closed beta -> store decision

## Objective

Bring ZubiLook from a mock-first MVP to a controlled closed beta with:

- a reproducible website deployment from GitHub;
- working and auditable patient and clinic submissions;
- published legal documents that match the real production behavior;
- a documented quality decision based on 10 consented selfies;
- real OTP, private photo storage, AI generation, clinics, and one-clinic lead delivery;
- verified user deletion and automatic 30-day photo deletion;
- enough beta evidence to make an App Store and Google Play decision.

The loop does not treat a deployed screen as a completed feature. Each gate closes only
after implementation, automated checks, a real smoke test, and evidence in the repo or
production system.

## Operating rules

1. `main` changes only through a focused PR with green CI.
2. After every merge, verify the actual file on `main` and the production deployment.
3. Enable one real integration at a time: Supabase -> Fal.ai -> notifications -> optional
   payments and analytics.
4. Never commit secrets. Public Supabase anon/publishable keys are allowed only where
   intended; service-role and provider secrets remain server-side.
5. Do not process real selfies until consent, private storage, access controls, and the
   deletion path are ready for the relevant environment.
6. Do not claim legal compliance from documents alone. The implementation, processor
   locations, operator notices, and retention controls must match the published text.
7. A smile output is always described as a visual simulation, not a diagnosis, treatment
   plan, medical recommendation, or guaranteed clinical result.
8. A lead belongs to one clinic selected by the user. The same lead is not resold.

## Current baseline

| Area | Current state | Gate status |
|---|---|---|
| Website | `web/` is synchronized with GitHub and deployed to `zubilook.com` | Closed |
| Website forms | Frontend fallback works; migration `0008` and consent metadata are merged; remote apply is pending | Open |
| Legal | Internal EN drafts and a release checklist exist; operator facts are unresolved | Blocked on facts |
| Phase 0 | Harness and real MediaPipe landmark detection are operational locally | Blocked on approved inputs/key |
| Backend | Production image/readiness, JWT guards, leads, retention, and pre-upload consent contract are implemented; Railway deployment is pending | Open |
| Flutter | OTP, clinics, leads, verified photo deletion, and the pre-upload consent gate are implemented; real-device E2E is pending | Open |
| Retention | Retryable hard deletion and the 30-day job exist; remote migration and Railway cron are pending | Release blocker |
| Beta | Not started | Open |

## Gate 1 - Website forms and Supabase

### Inputs

- Reconnected Supabase connector for project `htclwrotnmhtbrdisqcu`.
- Approved migration `supabase/migrations/0008_waitlist.sql`.
- Public anon/publishable key from the same project.

### Work

1. Merge the schema and consent-metadata PR after CI passes.
2. Apply migration `0008` once and inspect the resulting tables, constraints, policies,
   and grants.
3. Confirm that anonymous clients can insert only valid consented submissions and cannot
   read, update, or delete the collected rows.
4. Add the public key to the website in a separate PR; keep the service-role key out of
   the browser and repository.
5. Deploy through Vercel from GitHub.
6. Submit one patient request and one clinic request on production.
7. Verify every field in Supabase: source, locale, consent flag, consent version,
   consent timestamp, contact details, and form-specific fields.
8. Run negative checks for missing consent and invalid field values.
9. Mark or remove test rows after verification.

### Exit evidence

- Green GitHub CI and successful Vercel production deployment.
- Two verified production rows with correct consent metadata.
- Anonymous read/update/delete attempts denied.
- Mailto fallback no longer used in the normal production path.

## Gate 2 - Legal publication

### Required facts from Selena

- Operator's full legal name or full individual name.
- Registration country and legal/postal address.
- Privacy and support email addresses.
- Initial beta geography: Russia, Uzbekistan, or both.
- Confirmed age rule; proposed beta default is 18+.
- Actual Supabase, Railway, Fal.ai, email, analytics, and error-monitoring regions.
- Status of required regulator notice/database registration in each launch country.

### Work

1. Build a production processor and data-flow register from enabled services only.
2. Resolve jurisdiction-specific lawful bases, cross-border processing, retention, and
   data-subject request procedures with qualified local review where required.
3. Finalize the canonical policy and terms without placeholders.
4. Produce reviewed RU, EN, and UZ versions with one version number and effective date.
5. Publish stable URLs under `zubilook.com`.
6. Link both documents from the footer, every website consent checkbox, first photo
   upload consent, profile/privacy controls, and clinic lead confirmation.
7. Verify that consent is unchecked by default and that the exact accepted version is
   stored.
8. Record legal approval and release version in the repo.

The code path uses migration `0012_photo_processing_consent.sql`: the authenticated
API records the accepted version and issues the exact private upload path before the
client can upload a selfie. This remains release evidence only after remote migration,
Flutter CI, and a real OTP/upload smoke test pass.

### Exit evidence

- No placeholders, future-tense behavior, or unverified compliance claims.
- RU/EN/UZ pages pass link, mobile layout, and language checks.
- Published text matches actual providers, regions, retention, and deletion behavior.
- Real-user photo beta is explicitly cleared for the selected geography.

## Gate 3 - Phase 0 quality Go/No-Go

### Inputs

- A folder containing exactly 10 consented test selfies selected for variation in
  lighting, skin tone, face shape, smile visibility, camera quality, and minor pose.
- `FAL_API_KEY` set locally, never pasted into code or committed.
- Test consent record and a defined secure deletion date for the input/output set.

### Execution

1. Validate file count, format, dimensions, face count, mouth visibility, and duplicates.
2. Freeze the input manifest and checksums before generation.
3. Run one defined style and configuration for all 10 inputs; do not tune per person.
4. Preserve request ID, provider, duration, cost, error, and output checksum.
5. Score each result from 1 to 5 on tooth realism, face preservation, boundary blending,
   style accuracy, and emotional response.
6. Review comparisons without changing scores after seeing aggregate results.
7. Publish `PHASE0_REPORT.md` with the matrix, failures, representative comparisons,
   costs, latency, configuration, and decision.

### Decision rule

- **GO:** overall average at least 3.5/5 and no criterion below 2.0.
- **ITERATE:** average 3.0-3.49; adjust mask/prompt once, rerun a versioned test.
- **NO-GO:** average below 3.0 or a recurring identity/face-preservation failure.

No production inference deployment follows a NO-GO. Borderline results are not rounded
up to pass.

## Gate 4 - Production backend foundation

### Work

1. Make the production Docker image install the ML dependencies and include or fetch the
   pinned Face Landmarker model reproducibly.
2. Add startup validation that rejects contradictory production settings, missing
   secrets, mock inference, wildcard CORS, or unavailable model assets.
3. Deploy to Railway with mock inference first and verify `/health` plus a separate
   dependency-aware readiness check.
4. Configure Supabase URL/service credentials, JWT verification configuration, Fal.ai,
   SMTP, Sentry, and allowed origins through Railway environment variables.
5. Turn on real services one by one, with a smoke test and rollback after each change.
6. Add structured request IDs, privacy-safe logs, timeout/retry policy, rate limits,
   payload limits, and alerting for generation and lead-delivery failures.
7. Document deployment, rollback, key rotation, incident response, and backup ownership.

### Exit evidence

- Production health/readiness green with `MOCK_AUTH=false` and, after Phase 0 GO,
  `MOCK_INFERENCE=false`.
- No secrets in Git history, client bundles, logs, or error payloads.
- One authorized real generation completes through Railway and private Supabase storage.
- A failed provider request produces a bounded, user-safe failure and an observable log.

## Gate 5 - OTP, private storage, and deletion

### Work

1. Replace the Flutter mock login with Supabase phone OTP request, verification, session
   refresh, logout, and expired-code handling.
2. Make the backend validate real user tokens and enforce row ownership.
3. Use private storage buckets and short-lived signed URLs; no public selfie/result URLs.
4. Upload only after explicit photo-processing consent and attach the accepted policy
   version to the user/generation record.
5. Make user deletion remove originals, generated files, related rows, sessions, and
   derived artifacts, while retaining only records legally required and disclosed.
6. Implement an idempotent scheduled job for hard deletion after 30 days.
7. Add a dry-run mode, metrics, failure retries, and an auditable deletion log without
   retaining the deleted image itself.
8. Test account deletion, single-generation deletion, expiry deletion, repeated jobs,
   partial failures, and missing objects.

### Exit evidence

- OTP works on a real allow-listed phone number and survives app restart.
- User A cannot access User B's rows or storage objects.
- Manual deletion removes a test image and row end to end.
- An artificially expired fixture is hard-deleted by the scheduled job and cannot be
  fetched with a new signed URL.

## Gate 6 - Clinics and one-clinic lead flow

### Work

1. Replace development seed clinics with explicitly approved pilot records and verified
   contact channels; keep unverified pricing labelled as a team estimate.
2. Connect the Flutter clinic list to the real API with city, loading, empty, error, and
   retry states.
3. Connect the lead form to the selected clinic and generation; validate name, phone,
   preferred time, and explicit transfer consent.
4. Enforce idempotency so repeated taps cannot create duplicate billable leads.
5. Persist one selected clinic per lead and prevent reassignment/resale through public
   endpoints.
6. Deliver the clinic notification through a production channel and record delivery
   status, retries, and manual recovery.
7. Verify the branded patient handoff without exposing permanent image URLs.

### Exit evidence

- One beta user selects one clinic, submits once, and creates one database row.
- The selected clinic receives the correct contact and visualization context.
- Another clinic cannot query the lead.
- Notification failure is visible and retryable without losing or duplicating the lead.

## Gate 7 - Closed beta

### Proposed beta scope

- Invite-only cohort; size is a team assumption to confirm before recruitment.
- Adults only until a guardian flow is legally and technically implemented.
- Payments disabled or clearly test-only unless the payment/legal gate is separately
  completed.
- Limited approved clinics and geography.

### Entry checklist

- Gates 1-6 closed for the selected geography.
- Release build, version, rollback, support contact, incident owner, and status channel.
- Test matrix covers supported devices, poor network, OTP expiry, bad photos, provider
  timeout, duplicate lead taps, data deletion, and app restart.
- Consent, privacy, terms, store privacy disclosures, and test-data handling approved.

### Evidence to collect

- Invite -> OTP -> upload -> successful generation funnel.
- Generation success/failure reasons and latency distribution.
- Quality score by input condition and recurring artifact types.
- Result-to-clinic intent and lead completion; these are beta measurements, not facts
  until observed.
- Crash/error rate, support incidents, notification delivery, and deletion-job success.
- Qualitative trust feedback on realism and medical framing.

### Exit decision

At beta close, publish `BETA_REPORT.md` with sample size, configuration, observed metrics,
incidents, unresolved privacy/security risks, and one of:

- **Store GO:** quality, stability, legal, deletion, and support gates passed.
- **Limited beta extension:** fixable issues with a named owner and retest date.
- **Store NO-GO:** recurring quality, privacy, security, or operational failure.

App Store and Google Play work begins only after this decision. Store submission is not
used as a substitute for beta validation.

## Immediate external dependencies

| Needed now | Owner | Unblocks |
|---|---|---|
| Reconnect Supabase and say `готово` | Selena | Gate 1 remote apply/key/real rows |
| Confirm operator and launch-jurisdiction facts | Selena | Gate 2 publication |
| Point to the approved 10-selfie folder | Selena | Gate 3 input validation |
| Set `FAL_API_KEY` in the local environment | Selena | Gate 3 real inference |
| Confirm pilot clinics and notification contacts | Selena | Gate 6 production leads |

## Agent-loop reporting

For each loop:

1. Read the current gate and production state.
2. Take the highest-priority unblocked action.
3. Run automated checks and a real smoke test where applicable.
4. Open a focused PR; wait for green CI; merge with an expected head SHA.
5. Verify GitHub `main` and the deployed artifact.
6. Update this plan, `SESSION_HANDOFF.md`, and the relevant evidence report.
7. Record an external blocker after two failed environment attempts and continue with
   independent work.
