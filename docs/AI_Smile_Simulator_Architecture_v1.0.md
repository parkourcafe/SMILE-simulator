> Auto-extracted plain text from the source `.docx` for readable reference. The `.docx` remains the canonical version.


AI Smile Simulator
System Architecture Specification
v1.0 — 28.06.2026 — Bali
Technical document for development team. Option 2: Inpainting + Flux.

1. System Overview
AI Smile Simulator is a cross-platform mobile application (iOS + Android) that allows users to upload a selfie, select a dental style, and receive an AI-generated visualization of their future smile. The system uses inpainting to modify only the mouth area, preserving the rest of the face.

The architecture follows a three-layer design: mobile client, API gateway, and inference backend. Supabase handles auth, database, and storage. A lightweight custom API layer orchestrates the ML pipeline and manages provider abstraction. Fal.ai provides inference.

1.1. High-Level Data Flow
The primary user flow through the system:

User opens app → registers/logs in via Supabase Auth (phone OTP or email).
User uploads selfie (camera or gallery) → photo sent to API Gateway.
API Gateway: validates photo → checks generation limit → preprocesses (resize, normalize).
ML Pipeline: MediaPipe Face Mesh detects mouth → generates binary mask → constructs prompt from style.
Inference: sends photo + mask + prompt to Fal.ai FLUX.1 Pro Fill → receives result image.
Post-processing: quality check → watermark (if free tier) → save to Supabase Storage.
Result returned to app → user sees before/after comparison.
User actions: save (paid), share (paid), find clinic, regenerate, or purchase pack.
If “Find clinic”: geo-filtered list of partner clinics → user submits lead form → clinic notified.

Critical constraint: generative API must NEVER be called directly from the mobile client. All inference goes through the API Gateway to protect API keys, enforce limits, and log costs.

2. Technology Stack
Layer
Technology
Why This Choice
Mobile client
Flutter 3.x (Dart)
Single codebase for iOS + Android. Mature, Google-backed. Saves 30–40% vs native.
State management
Riverpod
Type-safe, testable, better than Provider for complex state. Alternative: BLoC.
Backend / API Gateway
Node.js (Express) or Python (FastAPI)
Lightweight API layer for inference orchestration. FastAPI preferred for ML pipeline integration.
Database
PostgreSQL via Supabase
Managed, free tier for MVP, real-time subscriptions, Row Level Security.
Auth
Supabase Auth
Phone OTP (critical for RU/UZ), email, social. Zero custom auth code.
File storage
Supabase Storage
Photos with auto-expiry. Signed URLs for privacy. CDN via Supabase.
Face detection
MediaPipe Face Mesh (468 landmarks)
Runs on-device (Flutter plugin) or server-side (Python). Free, fast, accurate.
Mask generation
Custom Python script
Uses Face Mesh landmarks 0–405 (mouth region) to generate binary mask PNG. ~50ms.
Inference
Fal.ai — FLUX.1 [pro] Fill
$0.05/megapixel. Best balance of quality/speed/cost for inpainting. Provider-abstracted.
Payments (RU)
YooKassa
Dominant Russian payment gateway. Cards, SBP, YooMoney. 2.8–3.5% commission.
Payments (UZ)
Click / Payme
Standard Uzbek payment gateways. UZS support.
Payments (global)
Apple IAP / Google Play Billing
Required for in-app purchases on respective stores.
Analytics
Mixpanel or Amplitude
Event tracking, funnels, cohorts. Free tier sufficient for MVP.
Error tracking
Sentry
Flutter + backend. Real-time crash/error monitoring.
Hosting
Railway or Render
API gateway hosting. Auto-deploy from GitHub. ~$5–25/mo for MVP.
CDN
Cloudflare
Free tier. DNS, SSL, caching, DDoS protection.
CI/CD
GitHub Actions
Automated testing + deployment on push to main.

3. Database Schema (PostgreSQL)
All tables use UUID primary keys, created_at/updated_at timestamps, and Row Level Security (RLS) via Supabase. Phone numbers stored with country code. Photos stored in Supabase Storage with signed URLs (not in DB).
3.1. users
Column
Type
Notes
id
uuid (PK)
Supabase Auth user ID
phone
text
With country code (+7..., +998...)
email
text (nullable)
Optional
display_name
text (nullable)
For clinic-facing lead form
city
text (nullable)
For geo-matching with clinics
free_gens_used
int (default 0)
Track free tier usage. Max = 1.
created_at
timestamptz
Auto
updated_at
timestamptz
Auto
3.2. generations
Column
Type
Notes
id
uuid (PK)

user_id
uuid (FK → users)

original_photo_url
text
Supabase Storage signed URL
result_photo_url
text (nullable)
Null until generation completes
mask_url
text (nullable)
Stored for debugging/retraining
style_id
uuid (FK → styles)
Selected dental style
status
enum
pending | processing | completed | failed
prompt
text
Constructed prompt sent to inference
inference_provider
text
fal_flux_pro_fill | replicate_flux | ...
inference_cost_usd
decimal(6,4)
Actual API cost tracked
inference_duration_ms
int
Time from request to response
quality_score
decimal(3,1) (nullable)
Manual or auto quality rating 1–5
has_watermark
boolean
True for free tier generations
error_message
text (nullable)
If status = failed
created_at
timestamptz

3.3. styles
Column
Type
Notes
id
uuid (PK)

name
text
e.g. “Natural White”, “Hollywood Smile”
name_ru
text
Russian localization
prompt_template
text
Template with {variables} for prompt construction
thumbnail_url
text
Preview image for style selector
is_premium
boolean
If true, only available in paid packs
sort_order
int
Display order in app
is_active
boolean
Soft enable/disable
3.4. packs
Column
Type
Notes
id
uuid (PK)

user_id
uuid (FK → users)

pack_type
enum
mini | main | extended | promo
generations_total
int
5, 20, 50 depending on pack
generations_used
int (default 0)
Decremented on each generation
price_amount
decimal(8,2)
149, 499, 899 (₽)
price_currency
text
RUB, UZS, USD
purchased_at
timestamptz

expires_at
timestamptz (nullable)
Optional pack expiry
3.5. payments
Column
Type
Notes
id
uuid (PK)

user_id
uuid (FK → users)

pack_id
uuid (FK → packs, nullable)
Linked pack
amount
decimal(10,2)

currency
text
RUB, UZS, USD
provider
enum
yookassa | click | payme | apple_iap | google_play
provider_payment_id
text
External payment ID for reconciliation
status
enum
pending | completed | failed | refunded
created_at
timestamptz

completed_at
timestamptz (nullable)


3.6. clinics
Column
Type
Notes
id
uuid (PK)

name
text
Clinic display name
city
text
Moscow, SPb, Tashkent
address
text
Full address
lat
decimal(9,6)
For geo-matching
lng
decimal(9,6)

phone
text
Contact phone
email
text
For lead notifications
website
text (nullable)

logo_url
text (nullable)

specialties
text[]
Array: veneers, whitening, implants, orthodontics
lead_price_rub
decimal(8,2)
Per-lead price for this clinic
status
enum
active | paused | trial
created_at
timestamptz

3.7. leads
Column
Type
Notes
id
uuid (PK)

user_id
uuid (FK → users)
Patient who requested
clinic_id
uuid (FK → clinics)
Target clinic
generation_id
uuid (FK → generations)
The smile simulation that triggered the lead
user_name
text
From lead form
user_phone
text
From lead form
preferred_time
text (nullable)
Morning / afternoon / evening
status
enum
new | notified | contacted | booked | completed | rejected
clinic_notified_at
timestamptz (nullable)
When clinic received the lead
clinic_responded_at
timestamptz (nullable)

lead_cost_rub
decimal(8,2)
What clinic pays for this lead
created_at
timestamptz


4. API Endpoints
All endpoints require Authorization: Bearer <supabase_jwt> except webhooks. Base URL: https://api.smilesim.app/v1
4.1. Auth (handled by Supabase)
Method
Endpoint
Description
POST
/auth/signup
Register with phone (OTP) or email
POST
/auth/verify-otp
Verify phone OTP code
POST
/auth/login
Login with existing credentials
POST
/auth/refresh
Refresh JWT token
GET
/auth/user
Get current user profile
4.2. Generation
Method
Endpoint
Description
POST
/api/generate
Upload photo + style_id → start generation. Returns generation_id.
GET
/api/generate/:id
Get generation status and result. Poll until status = completed.
POST
/api/generate/:id/retry
Retry a failed generation (same photo, same/different style).
GET
/api/generate/history
List user’s past generations (paginated).
DELETE
/api/generate/:id
Delete a generation and its photos.

POST /api/generate flow: (1) Check user has remaining generations (free or pack). (2) Validate photo (format, size, face detected). (3) Decrement generation count. (4) Start async pipeline. (5) Return generation_id with status=pending. Client polls GET /:id until completed.
4.3. Packs & Payments
Method
Endpoint
Description
GET
/api/packs/available
List purchasable pack types with prices (localized by currency).
POST
/api/packs/purchase
Initiate purchase. Body: { pack_type, provider }. Returns payment URL.
GET
/api/packs/my
List user’s active packs with remaining generations.
POST
/api/webhooks/yookassa
YooKassa payment confirmation webhook (HMAC-verified).
POST
/api/webhooks/click
Click payment confirmation webhook.
4.4. Styles
Method
Endpoint
Description
GET
/api/styles
List available styles (filtered by user’s pack tier).
4.5. Clinics & Leads
Method
Endpoint
Description
GET
/api/clinics
List partner clinics. Query: ?city=Moscow&lat=55.75&lng=37.62&radius=10km
POST
/api/leads
Submit lead form. Body: { clinic_id, generation_id, name, phone, preferred_time }
GET
/api/clinic/dashboard
[B2B] Clinic sees their leads. Auth: clinic API key.
PATCH
/api/clinic/leads/:id
[B2B] Clinic updates lead status (contacted, booked, etc.).
4.6. Admin
Method
Endpoint
Description
GET
/api/admin/stats
Generation count, cost, success rate, revenue, leads. Auth: admin key.
GET
/api/admin/generations
List all generations with quality scores. For QA review.
POST
/api/admin/styles
Create/update styles (prompt templates, thumbnails).
POST
/api/admin/clinics
Create/update clinic records.

5. ML Pipeline: Mouth Inpainting
5.1. Pipeline Steps
The pipeline runs server-side (API Gateway) as an async job. Average total time: 5–15 seconds.

Step
Process
Technology
Time
Notes
1
Photo validation
Python (Pillow)
<100ms
Check: format (JPG/PNG/HEIC), min 512px, max 4096px, file size <10MB.
2
Resize & normalize
Python (Pillow)
<100ms
Resize to 1024x1024 (square crop centered on face). Normalize lighting.
3
Face detection
MediaPipe Face Mesh
200–500ms
468 landmarks. Detect face, validate: exactly 1 face, frontal, mouth visible.
4
Mouth mask generation
Custom Python
50–100ms
Extract landmarks 0–17 (lip outer), 61–68 (lip inner). Create binary mask with 15–20px feathered edge.
5
Prompt construction
Python
<10ms
Template: “Beautiful {style} teeth, natural-looking, photorealistic, same skin tone and lighting”
6
Inpainting
Fal.ai FLUX.1 Pro Fill
3–8s
Send: image + mask + prompt. Receive: result image. Cost: ~$0.05/MP.
7
Quality check
Python (heuristic)
100–200ms
Check: face still matches (SSIM on non-mask area), no extreme artifacts.
8
Watermark
Python (Pillow)
<50ms
If free tier: semi-transparent diagonal “AI Smile Simulator” watermark.
9
Save & respond
Supabase Storage
200–500ms
Upload result to storage, update generation record, notify client.
5.2. Prompt Templates by Style
Style
Prompt Template
Natural White
Beautiful naturally white teeth, slight improvement in alignment, same lip shape and skin tone, photorealistic, maintain original lighting and shadows
Straight Smile
Perfectly aligned straight teeth, natural white shade, no gaps, same lip shape, photorealistic dental result, maintain skin texture
Veneer Effect
Professional dental veneer result, uniform tooth shape and size, bright white but natural-looking, celebrity-quality smile, same lip contour
Hollywood Smile
Brilliant white Hollywood smile, perfect symmetry, gleaming teeth, red carpet ready, maintain natural lip shape and facial features

Prompt engineering is critical. Small changes in prompt wording can dramatically affect quality. Maintain a prompt version log and A/B test variants on the 30-selfie test set.
5.3. Face Mesh Landmarks for Mouth Mask
MediaPipe Face Mesh provides 468 facial landmarks. The mouth region uses these landmark groups:
Outer lip contour: landmarks 0, 267, 269, 270, 409, 291, 375, 321, 405, 314, 17, 84, 181, 91, 146, 61, 185, 40, 39, 37
Inner lip contour: landmarks 78, 95, 88, 178, 87, 14, 317, 402, 318, 324, 308, 415, 310, 311, 312, 13, 82, 81, 80, 191
Mask strategy: fill outer contour as white on black background, expand by 15–20px (cv2.dilate), apply Gaussian blur for feathered edge (sigma=5–8).
Edge feathering is critical: sharp mask edges create visible “pasted-in” artifacts at the boundary.
5.4. Provider Abstraction Layer
The inference step is wrapped in a provider abstraction interface. This allows swapping Fal.ai for Replicate, RunPod, or a self-hosted model without changing the pipeline.

Method
Input
Output
generate(image, mask, prompt, config)
Base64 image, base64 mask, text prompt, provider config
Result image (base64), inference_cost, duration_ms

Supported providers (Phase 1: Fal.ai only, Phase 2+: add alternatives):
Provider
Model
Cost
Speed
Notes
Fal.ai
FLUX.1 [pro] Fill
$0.05/MP
3–8s
Primary. Best quality/cost ratio for inpainting.
Fal.ai
FLUX.1 [dev] Inpainting + LoRA
$0.035/MP
3–10s
Phase 2: custom LoRA for dental-specific quality.
Replicate
FLUX Inpainting
~$0.03–0.08
5–15s
Backup provider. Slower cold starts.
Self-hosted
Custom LoRA on RunPod/Vast
~$0.01–0.03
2–5s
Phase 3: lowest cost at scale, requires ops.

6. Screen Architecture (Flutter)
6.1. Screen Map
Screen
Route
Key Components
Auth Required
Splash
/ 
Logo animation, version check, auto-login
No
Onboarding
/ onboarding
3 swipeable pages: what it does, how it works, privacy
No
Login
/ login
Phone OTP input (primary) or email. Country selector (+7, +998).
No
OTP Verify
/verify
6-digit code input, auto-submit, resend timer
No
Home
/home
Upload button (CTA), recent results carousel, remaining gens counter
Yes
Camera/Upload
/upload
Camera capture or gallery picker. Photo guidelines overlay.
Yes
Photo Preview
/preview
Cropped photo preview. Face validation indicator. “Continue” button.
Yes
Style Selector
/styles
Grid of style thumbnails. Premium styles locked if no pack.
Yes
Generating
/generating
Animated loading (teeth sparkle animation). ~5–15 sec. Cancel option.
Yes
Result
/result/:id
Before/after slider. Actions: save, share, find clinic, retry, new photo.
Yes
Paywall
/paywall
Pack cards (149/499/899 ₽). Benefits list. Purchase button. Triggered on limit.
Yes
History
/history
Grid of past generations. Tap to view result.
Yes
Find Clinic
/clinics
Map + list of partner clinics. Distance-sorted. “Book consultation” button.
Yes
Lead Form
/lead/:clinic_id
Name, phone, preferred time. Attached: generation photo.
Yes
Lead Sent
/lead/sent
Confirmation. “Clinic will contact you within 24 hours.”
Yes
Profile
/profile
Name, phone, active packs, generation count, support link, delete account.
Yes
6.2. Navigation Flow
First launch: Splash → Onboarding → Login → Home
Returning user: Splash → Home (auto-login)
Generation: Home → Upload → Preview → Styles → Generating → Result
Free limit hit: Result → “Get More” → Paywall → (purchase) → Home
Find clinic: Result → “Find Clinic” → Clinics → Lead Form → Lead Sent
History: Home → History → Result (view past generation)
6.3. Key UX Decisions
Photo guidelines overlay on camera screen: “Face the camera. Open your mouth slightly. Good lighting.” Reduces bad uploads.
Before/after slider on result screen: draggable divider between original and AI result. Most engaging format.
Watermark on free result: semi-transparent, cannot be cropped out. “Remove watermark” button leads to paywall.
Paywall appears at the moment of peak emotion (after seeing the result), not before.
“Find a clinic” button appears on every result screen. Not hidden. Not aggressive. Just there.
Generation counter visible on home screen: “0 of 1 free generation used” or “12 generations remaining.”

7. Payment System
7.1. Payment Flows
Provider
Region
Flow
Commission
YooKassa
Russia
User selects pack → API creates YooKassa payment → redirect to YooKassa checkout → user pays (card/SBP/YooMoney) → webhook confirms → pack activated
2.8–3.5%
Click / Payme
Uzbekistan
Similar redirect flow. UZS currency.
2–4%
Apple IAP
iOS global
StoreKit 2 in-app purchase. Apple handles checkout.
15–30%
Google Play Billing
Android global
Google Play billing library. Google handles checkout.
15–30%

Apple/Google commissions (15–30%) significantly eat into margins on small packs. Consider: in-app packs for convenience, but promote web checkout (YooKassa direct) for better margins via promo codes or website purchase flow.
7.2. Webhook Security
YooKassa: verify webhook signature (HMAC-SHA256 with secret key). Reject unsigned requests.
Idempotency: process each payment_id only once. Store processed IDs in a dedup table.
Retry logic: if pack activation fails after payment confirmed, queue for retry. Never lose a payment.
8. B2B Lead System
8.1. Lead Lifecycle
User completes generation → taps “Find a clinic” → selects clinic → fills lead form.
Lead created in DB with status = new. Includes: user name, phone, generation result photo.
Clinic notified instantly via WhatsApp Business API (or email fallback). Message includes patient photo + AI result.
Clinic updates lead status: contacted → booked → completed (or rejected).
Billing: clinic charged per lead (new status). Monthly invoice or prepaid credit balance.
8.2. Lead Notification Message (WhatsApp template)
Template for clinic notification:

Новый пациент из AI Smile Simulator!

Имя: {user_name}
Тел: {user_phone}
Желаемое время: {preferred_time}

Пациент хочет улучшить улыбку. AI-визуализация приложена.

Свяжитесь в течение 24 часов для максимальной конверсии.
8.3. Clinic Dashboard (Phase 2)
Simple web dashboard (Next.js or React). Auth via unique clinic API key.
Shows: new leads (with patient photo + AI result), lead history, conversion stats, invoice.
MVP: no dashboard. Leads sent via WhatsApp + email. Dashboard built when 15+ clinics active.

9. Analytics & Metrics
9.1. Key Events
Event
When
Properties
app_open
App launched
user_id, platform, version
photo_uploaded
User submits photo for generation
user_id, source (camera/gallery), file_size
photo_rejected
Photo fails validation
user_id, reason (no_face, multiple_faces, too_dark, ...)
style_selected
User picks a dental style
user_id, style_id, style_name
generation_started
Pipeline begins processing
user_id, generation_id, style_id
generation_completed
Result ready
user_id, generation_id, duration_ms, cost_usd, provider
generation_failed
Pipeline error
user_id, generation_id, error_type, error_message
result_viewed
User sees before/after
user_id, generation_id, time_spent_ms
result_saved
User saves (paid only)
user_id, generation_id
result_shared
User shares (paid only)
user_id, generation_id, share_target
paywall_shown
Paywall screen displayed
user_id, trigger (limit_reached / premium_style / save)
pack_purchased
Payment completed
user_id, pack_type, amount, currency, provider
clinic_tap
User taps “Find a clinic”
user_id, generation_id
lead_submitted
User submits lead form
user_id, clinic_id, generation_id
9.2. Key Metrics (Dashboard)
Metric
Formula
Target (MVP)
DAU / MAU
Daily/monthly active users
>100 DAU by month 2
Generations/user
Total gens / unique users
2–3 avg
Free → paid conversion
Paid users / total users with 1+ gen
5–8%
Cost per generation
Total API spend / total generations
<$0.10
Effective cost per GOOD gen
API spend / successful generations
<$0.15
Revenue per user
Total revenue / total users
>₽50
Clinic tap rate
clinic_tap events / result_viewed events
>10%
Lead submission rate
lead_submitted / clinic_tap
>30%
Lead cost
(infra + API cost per lead) / leads generated
<₽200
Clinic satisfaction
Leads converted to bookings / total leads
>20%

10. Security & Privacy
10.1. Data Protection (152-ФЗ Compliance)
User consent screen before first photo upload: explicit opt-in for facial data processing.
Data minimization: store only what’s needed. Original photos auto-deleted after 30 days.
Right to deletion: “Delete my account” in profile immediately removes all photos and personal data.
No third-party data sharing except inference provider (Fal.ai) and payment provider.
Privacy policy and terms of use: required before registration. In Russian and Uzbek.
10.2. API Security
Fal.ai API key: stored server-side only. Never in client code or client-accessible storage.
Supabase RLS: users can only read/write their own data. Admin endpoints require separate auth.
Rate limiting: max 5 generations per minute per user. Prevents abuse and cost overruns.
Input validation: photo max 10MB, accepted formats only, face detection must pass before inference.
Webhook signature verification for all payment callbacks.
10.3. Photo Handling
Photos uploaded via signed URL (not through API gateway body) to reduce bandwidth and attack surface.
Original photos stored in private Supabase Storage bucket. Access only via signed URLs with expiry.
Result photos: same private bucket. Signed URL generated on-demand for display.
No photos served via public URLs. No photo caching on CDN.
Medical disclaimer: displayed on every result screen. “Visualization only, not medical advice.”
11. Infrastructure & Deployment
11.1. MVP Infrastructure
Component
Service
Cost/Month
Notes
API Gateway
Railway (Starter)
$5–25
Auto-deploy from GitHub. Scales on demand.
Database + Auth + Storage
Supabase (Pro)
$25
500MB DB, 100GB storage, 50K MAU auth.
Inference
Fal.ai (pay-per-use)
$50–500
Scales with generation volume.
CDN + DNS
Cloudflare (Free)
$0
SSL, caching, DDoS.
Error tracking
Sentry (Developer)
$0
Free for 5K events/month.
Analytics
Mixpanel (Starter)
$0
Free for 20M events/month.
App stores
Apple ($99/yr) + Google ($25)
~$10
Amortized monthly.
Domain
smilesim.app
~$1
Annual domain registration.
TOTAL

$91–561/mo
Scales with usage, not with team size.
11.2. Deployment Pipeline
Developer pushes to GitHub main branch.
GitHub Actions runs: lint → test → build.
If passing: auto-deploy API to Railway.
Flutter: build iOS (Xcode Cloud) + Android (Fastlane) → submit to App Store / Play Store.
Database migrations: run via Supabase CLI on deploy.
11.3. Monitoring
Sentry: crash reports and error tracking for Flutter app and API.
Railway metrics: CPU, memory, request count, latency.
Supabase dashboard: DB size, auth events, storage usage.
Custom Slack alerts: generation failures, payment errors, cost spikes.

12. Development Phases
Phase
Scope
Timeline
Deliverable
Phase 0: Spike
Test inpainting quality with 10 selfies via Fal.ai playground. No code.
2–3 days
Go/no-go on FLUX Pro Fill quality.
Phase 1: Skeleton
Flutter app shell (upload, preview, result), Supabase setup, basic API gateway.
Week 1–2
App that uploads a photo and displays it back.
Phase 2: Pipeline
MediaPipe face mesh + mask generation + Fal.ai integration. End-to-end generation.
Week 2–3
First AI-generated smile inside the app.
Phase 3: Monetization
YooKassa integration, pack purchase flow, watermark logic, generation limits.
Week 3–4
User can buy a pack and generate paid results.
Phase 4: Quality
30-selfie test, prompt tuning, mask edge improvements, error handling.
Week 4–5
Quality scorecard ≥3.5/5. Go/no-go for beta.
Phase 5: B2B
Clinic database, “Find a clinic” screen, lead form, WhatsApp notification.
Week 5–6
First lead sent to a partner clinic.
Phase 6: Launch
App Store / Play Store submission, closed beta, partner demo.
Week 6–7
Live app with first users and clinic partners.
13. Open Technical Questions
Question
Options
Decision Needed By
API Gateway language
Python (FastAPI) vs Node.js (Express)
Phase 0 (before coding starts)
Face detection: on-device or server?
On-device (Flutter MediaPipe plugin) vs server-side (Python)
Phase 1
Photo upload: direct to Supabase or via API?
Direct (signed URL) vs API proxy
Phase 1
Multiple faces handling
Reject photo vs let user select face
Phase 2
Generation polling vs WebSocket
Client polls GET /generate/:id vs real-time push
Phase 2
Apple IAP vs web-only checkout
IAP required by Apple rules if app is free+purchases
Phase 3 (before App Store submission)
Clinic notification: WhatsApp vs email vs both
WhatsApp Business API requires approval; email is simpler MVP
Phase 5
Result image resolution
1024x1024 vs match original photo size
Phase 2 (affects cost)

Recommendation: start with Python FastAPI (better for ML pipeline), server-side face detection (more control), direct-to-Supabase upload (less API load), client polling (simpler than WebSocket for MVP), web checkout first (avoid Apple 30% tax), email notification (ship faster, add WhatsApp in Phase 2).

Version 1.0 | 28.06.2026 | Bali | Technical document for development team.
