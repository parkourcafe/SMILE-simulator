# CLAUDE.md — AI Smile Simulator

> Project constitution for Claude instances. Always-load core.
> Version 1.0 | 28.06.2026

## Identity

- **Product:** AI Smile Simulator — мобильное приложение (iOS + Android), которое показывает пользователю его будущую улыбку с помощью AI-inpainting.
- **Business model:** B2C → B2B lead generation. Пользователь бесплатно видит свою будущую улыбку → хочет сделать по-настоящему → приложение связывает его с клиникой-партнёром → клиника платит за лид.
- **Stage:** Pre-MVP. Документация готова, код ещё не написан. Следующий шаг — Phase 0 spike test (Fal.ai playground, 10 селфи).
- **Markets:** Россия (Москва, СПб — первые), Узбекистан (Ташкент — тест).
- **Language rules:** Код и комментарии — English. Документы для партнёров — English. Внутренняя коммуникация с Селеной — Russian. UI приложения — Russian (primary) + English.

## Tech Stack (locked)

| Layer | Technology | Why |
|---|---|---|
| Mobile | Flutter 3.x (Dart) | Single codebase iOS + Android |
| State mgmt | Riverpod | Type-safe, testable |
| Backend API | Python FastAPI | Best for ML pipeline integration |
| Database | PostgreSQL via Supabase | Managed, RLS, free tier for MVP |
| Auth | Supabase Auth (phone OTP) | Zero custom auth code |
| Storage | Supabase Storage | Photos with signed URLs, auto-expiry |
| Face detection | MediaPipe Face Mesh | 468 landmarks, server-side (Python) |
| Mask generation | Custom Python (OpenCV) | From Face Mesh mouth landmarks |
| Inference | Fal.ai — FLUX.1 [pro] Fill | $0.05/MP, best quality/cost for inpainting |
| Payments RU | YooKassa | Cards, SBP, YooMoney |
| Payments UZ | Click / Payme | UZS support |
| Analytics | Mixpanel | Event tracking, funnels |
| Error tracking | Sentry | Flutter + backend |
| Hosting | Railway | Auto-deploy, ~$5–25/mo |
| CDN | Cloudflare (free) | SSL, caching, DDoS |
| CI/CD | GitHub Actions | Lint → test → deploy |

## Architecture (summary)

```
User → Flutter App → Supabase Auth (phone OTP)
                    → Upload photo → Supabase Storage (signed URL)
                    → API Gateway (FastAPI)
                        → Validate photo (format, size, face)
                        → Check generation limit
                        → Resize to 1024x1024
                        → MediaPipe Face Mesh → detect mouth
                        → Generate binary mask (landmarks 0–17 outer, 61–68 inner, 15–20px feather)
                        → Construct prompt from style template
                        → Send image + mask + prompt → Fal.ai FLUX.1 Pro Fill
                        → Receive result
                        → Quality check (SSIM on non-mask area)
                        → Watermark (if free tier)
                        → Save to Supabase Storage
                    ← Result image returned to app
                    → User sees before/after slider
                    → "Find a clinic" → lead form → clinic notified via WhatsApp/email
```

**Critical rule:** Inference API NEVER called from mobile client. All through API Gateway.

## Database Tables

7 tables in Supabase PostgreSQL: `users`, `generations`, `styles`, `packs`, `payments`, `clinics`, `leads`. Full schema in `Architecture_Spec_v1.0.docx`, section 3.

## Key Business Decisions (locked)

These are decided. Do not re-open or suggest alternatives unless explicitly asked.

- **Technical path:** Option 2 (Inpainting + Flux). Not Option 1 (generic prompt) or Option 3 (custom LoRA — Phase 2 only).
- **Revenue model:** B2B per-lead (primary). B2C packs (secondary, funnel).
- **Free tier:** 1 generation with watermark. Not 3 free without watermark.
- **B2C pricing (RUB):** Mini 149₽ (5 gens), Main 499₽ (20 gens), Extended 899₽ (50 gens).
- **B2B pricing:** 500–1,500₽ per qualified lead. Phase 2: widget 5,000–15,000₽/mo. Phase 3: SaaS.
- **Competitor positioning:** NOT "zero competitors." SmileVision (Russia, B2B, 168+ clinics) already exists. Our differentiation: B2C funnel → leads for clinics. Different category.
- **Medical disclaimer:** All results framed as "visual simulation, not medical recommendation." On every result screen.
- **Data privacy:** 152-ФЗ compliance. Photos auto-delete after 30 days. Consent before first upload.

## Competitive Context

| Competitor | Market | Model | Our advantage |
|---|---|---|---|
| SmileVision | Russia | B2B SaaS for dentists, 3K–30K₽/mo | We build patient acquisition funnel, not clinic-side tool |
| Teethsi | Global/RU | B2C app, in-app purchases | No B2B integration, no clinic lead flow |
| SmileViz | USA | B2B SaaS $299–399/mo | Not in CIS, no B2C funnel, too expensive for RU |
| Simmetry | USA | B2B widget + lead gen | Not in CIS, no Russian language |
| denta.bot | UK | White-label widget | Not in CIS |

**Positioning statement:** "SmileViz quality at 2–3x lower price, with B2C funnel as built-in demand engine for clinic partners."

**Never say:** "zero competitors," "first in CIS," "no competition." **Always say:** "early-stage market, category not yet dominated."

## ML Pipeline Details

### Mouth Mask Landmarks (MediaPipe Face Mesh)

- **Outer lip:** 0, 267, 269, 270, 409, 291, 375, 321, 405, 314, 17, 84, 181, 91, 146, 61, 185, 40, 39, 37
- **Inner lip:** 78, 95, 88, 178, 87, 14, 317, 402, 318, 324, 308, 415, 310, 311, 312, 13, 82, 81, 80, 191
- **Mask strategy:** Fill outer contour → dilate 15–20px → Gaussian blur sigma 5–8 for feathered edge
- **Edge feathering is critical:** Sharp edges = "pasted-in" look = user does not trust result

### Prompt Templates

| Style | Prompt |
|---|---|
| Natural White | Beautiful naturally white teeth, slight improvement in alignment, same lip shape and skin tone, photorealistic, maintain original lighting and shadows |
| Straight Smile | Perfectly aligned straight teeth, natural white shade, no gaps, same lip shape, photorealistic dental result, maintain skin texture |
| Veneer Effect | Professional dental veneer result, uniform tooth shape and size, bright white but natural-looking, celebrity-quality smile, same lip contour |
| Hollywood Smile | Brilliant white Hollywood smile, perfect symmetry, gleaming teeth, red carpet ready, maintain natural lip shape and facial features |

### Provider Abstraction

Inference is wrapped in an abstraction layer. MVP uses Fal.ai only. Phase 2+ can swap to Replicate, RunPod, or self-hosted LoRA without pipeline changes.

```python
# Interface
async def generate(image: bytes, mask: bytes, prompt: str, config: ProviderConfig) -> GenerationResult:
    # Returns: result_image, cost_usd, duration_ms
```

### Fal.ai API

- **Endpoint:** `fal-ai/flux-pro/v1/fill`
- **Cost:** $0.05 per megapixel
- **Input:** image (base64), mask_image (base64), prompt (text)
- **Output:** result image
- **Latency:** 3–8 seconds

## Screen Map (Flutter)

16 screens. Key routes:

- `/` → Splash
- `/onboarding` → 3 swipeable pages
- `/login` → Phone OTP (primary)
- `/home` → Upload CTA + recent results + remaining gens counter
- `/upload` → Camera/gallery + photo guidelines overlay
- `/preview` → Cropped preview + face validation
- `/styles` → Style grid (premium locked if no pack)
- `/generating` → Loading animation (~5–15 sec)
- `/result/:id` → Before/after slider + actions (save, share, find clinic, retry)
- `/paywall` → Pack cards (149/499/899₽)
- `/clinics` → Map + list of partner clinics
- `/lead/:clinic_id` → Lead form (name, phone, time)
- `/history` → Past generations grid
- `/profile` → Settings, packs, delete account

### Key UX Rules

- Paywall appears AFTER result (peak emotion), not before
- Watermark cannot be cropped out — "Remove watermark" → paywall
- "Find a clinic" button on EVERY result screen — visible but not aggressive
- Photo guidelines overlay on camera: "Face camera. Open mouth slightly. Good lighting."
- Before/after slider (draggable divider) — most engaging result format

## Development Phases

| Phase | Scope | Timeline |
|---|---|---|
| 0: Spike | Test inpainting with 10 selfies on Fal.ai playground. No code. | 2–3 days |
| 1: Skeleton | Flutter app shell + Supabase + basic API gateway | Week 1–2 |
| 2: Pipeline | MediaPipe + mask + Fal.ai integration. End-to-end generation. | Week 2–3 |
| 3: Monetization | YooKassa + pack purchase + watermark + limits | Week 3–4 |
| 4: Quality | 30-selfie test + prompt tuning + mask improvements | Week 4–5 |
| 5: B2B | Clinic DB + "Find clinic" + lead form + WhatsApp notification | Week 5–6 |
| 6: Launch | App Store / Play Store submission + closed beta | Week 6–7 |

## Quality Criteria (for generations)

5 criteria, scale 1–5. Minimum for launch: average ≥3.5, no single criterion <2.0.

1. **Tooth realism** — Do teeth look natural? No "photoshop" feel.
2. **Face preservation** — Rest of face unchanged (lips, skin, lighting).
3. **Boundary blending** — Seamless transition at mask edge, no "pasted-in" look.
4. **Style accuracy** — Clear difference between style options.
5. **Emotional response** — Would user show this to a friend? "Wow" factor.

**Go/No-Go:**
- ≥3.5 avg → GO to beta
- 3.0–3.4 → Iterate pipeline, retest in 1 week
- <3.0 → Fundamental pipeline changes needed

## Source Discipline

When writing documents, presenting data, or making claims:

| Type | Rule |
|---|---|
| Verified facts | Pricing from official sites, app store data. Can state as fact with source. |
| Vendor claims | ROI, conversion metrics claimed by competitors. Mark as "vendor claim" or "competitor states." |
| Team estimates | SAM/SOM, unit economics, cost projections. Mark as "team estimate." |
| Assumptions | Conversion rates, lead quality, clinic willingness to pay. Mark as "assumption to validate." NEVER present as fact. |

**Rule:** No assumption may be presented as fact to partners or clinics until validated by pilot data.

## Budget

- **MVP total:** $12,000–20,000 (outsourced to CIS developers at $25–40/hr).
- **Tranches:**
  - T1: $5K–8K → app skeleton + inpainting pipeline
  - T2: $3K–5K → testing + legal + monetization (released only if prototype passes quality test)
  - T3: $2K–4K → launch + marketing + first 5 clinic partnerships
  - Contingency: $2K–3K
- **Monthly operating costs post-launch:** $155–785/mo (Supabase $25 + Fal.ai $100–500 + hosting $20–50 + misc).

## Working Rules for Claude

- **Language:** Follow Selena's language. Russian question → Russian answer. Code → English.
- **No re-litigation:** Don't suggest changing locked decisions (tech stack, pricing, Option 2 vs 3, etc.) unless Selena explicitly asks.
- **Text review protocol:** ANY text — rate 1–100, identify 3 critical flaws. If <90 → argue fixes. If ≥95 → execute.
- **Decision format:** Score on 100-point scale. If 85+ → just deliver. If <85 → state what's wrong briefly.
- **Source honesty:** Never fabricate facts. If unsure → say so. Mark estimates vs facts.
- **Competitive honesty:** SmileVision exists. Never claim "no competitors." Claim: "category not yet dominated."
- **Medical disclaimer awareness:** All user-facing text must avoid medical claims. "Visualization" not "diagnosis."
- **Date/time:** Start every message with DD.MM.YYYY | HH:MM | Bali.
- **File outputs:** All documents include creation date, time, location in header/footer.
- **Tone:** Smart friend, direct, no flattery. Concrete solutions over advice. If idea is bad → say why + give better option.

## Key Documents

| Document | Version | Purpose |
|---|---|---|
| Partner Brief | v2.5 | For partner meetings. Business model, competitors, pricing, budget, ask. |
| Architecture Spec | v1.0 | For dev team. Tech stack, DB schema, API endpoints, ML pipeline, screens. |
| CLAUDE.md | v1.0 | This file. Project constitution for Claude instances. |

## Contacts

- **Selena** — Founder. All decisions go through her.
- **Partner** — TBD (Russia/Uzbekistan). Business + potentially clinic access.
- **Developer** — TBD (CIS, Flutter + Python). Hired after partner confirms Tranche 1.

## Next Actions

- ☐ Phase 0 spike: test 10 selfies on Fal.ai FLUX Pro Fill playground
- ☐ Partner meeting: present v2.5 brief, get decisions on 3 asks
- ☐ If GO: hire Flutter+Python developer, start Phase 1
- ☐ Collect 20–30 test selfies (diverse demographics)
- ☐ Identify 5 pilot clinics in Moscow (cosmetic dentistry focus)
