# CLAUDE.md — AI Smile Simulator
> Project constitution for Claude instances (chat + Claude Code). Always-load core.
> Version 1.1 | 02.07.2026 | Changelog: synced with Architecture v1.1 (4 conversion enhancements), competitor update (Fixmysmile, Teethsi 1.2★), review protocol aligned to 1–5 scale, engineering rules for Claude Code added.

---

## Identity

**Product:** AI Smile Simulator — мобильное приложение (iOS + Android), которое показывает пользователю его будущую улыбку с помощью AI-inpainting.

**Business model:** B2C → B2B lead generation. Пользователь бесплатно видит свою будущую улыбку → хочет сделать по-настоящему → приложение связывает его с клиникой-партнёром → клиника платит за лид (500–1,500₽).

**Stage:** Documentation complete (Partner Brief v2.6, Architecture Spec v1.1). Next: repo init → Claude Code agent build, Phases 1–5.

**Markets:** Россия (Москва, СПб — первые), Узбекистан (Ташкент — тест).

**Language rules:** Код, комментарии, коммиты — English. Документы для партнёров — English. Коммуникация с Селеной — Russian. UI приложения — Russian (primary) + English.

---

## Tech Stack (locked)

| Layer | Technology | Notes |
|-------|-----------|-------|
| Mobile | Flutter 3.x (Dart) | Single codebase iOS + Android |
| State mgmt | Riverpod | Type-safe, testable |
| Backend API | Python 3.11+ FastAPI | ML pipeline orchestration |
| Database | PostgreSQL via Supabase | Local dev: Docker Postgres until Supabase project exists; migrations Supabase-compatible SQL |
| Auth | Supabase Auth (phone OTP) | MOCK_AUTH flag until creds provided |
| Storage | Supabase Storage | Signed URLs, auto-expiry 30 days |
| Face detection | MediaPipe Face Mesh | **Hybrid (resolved v1.1):** on-device live pre-check (advisory) + server-side authoritative |
| Mask generation | Python (OpenCV) | From Face Mesh mouth landmarks |
| Inference | Fal.ai — FLUX.1 [pro] Fill | $0.05/MP. MOCK_INFERENCE flag until key provided |
| Payments RU | YooKassa | MOCK_PAYMENTS flag until creds |
| Payments UZ | Click / Payme | Phase: post-MVP for UZ launch |
| Analytics | Mixpanel | Event contract in Architecture §9 |
| Errors | Sentry | Behind SENTRY_DSN env |
| Hosting | Railway | Auto-deploy from GitHub |
| CI/CD | GitHub Actions | lint → test → build |

---

## Architecture (summary, v1.1)

```
User → Flutter App
  → LIVE PRE-CHECK (v1.1): on-device MediaPipe over camera preview.
    Shutter gated until: 1 frontal face, mouth visible, light OK, sharp, distance OK.
    Real-time RU hints. Blocks fire precheck_blocked(reason).
  → Supabase Auth (phone OTP; MOCK_AUTH locally)
  → Upload photo → Storage (signed URL)
  → API Gateway (FastAPI):
      validate → limits → resize 1024x1024 → Face Mesh (authoritative)
      → mouth mask (outer 0–17, inner 61–68 landmark sets; dilate 15–20px; Gaussian feather σ5–8)
      → prompt from style template
      → Provider abstraction → Fal.ai FLUX.1 Pro Fill (or MockProvider)
      → quality check (SSIM non-mask area) → watermark if free → save
  → GENERATION THEATER (v1.1): 5–15s staged messages
    ("Анализируем улыбку → Подбираем форму → Выравниваем тон") + social proof.
  → Result: before/after slider
    + COST-ESTIMATE BLOCK (v1.1): "Такая улыбка в {city}: {range}₽" from price_estimates
    + CTA "Узнать точную цену в клинике рядом" → lead form
  → ACTION-LOCKED PAYWALL (v1.1): fires on 2nd generation tap / watermark removal / save.
    Never on a timer. Multi-page (value → plans).
  → Lead submitted → clinic notified (email MVP / WhatsApp Phase 2)
  → BRANDED RESULT DELIVERY (v1.1): patient gets before/after under CLINIC's brand
    ("Клиника X получила вашу заявку, вот ваша визуализация").
```

**Critical rule:** Inference API NEVER called from mobile client. All through API Gateway.

---

## Database — 8 tables

`users`, `generations`, `styles`, `packs`, `payments`, `clinics`, `leads`, `price_estimates` (v1.1: city × style × treatment_label × price_min/max × currency). Full schema: Architecture Spec v1.1 §3. RLS via Supabase.

---

## Key Business Decisions (locked)

Do not re-open unless Selena explicitly asks.

1. **Technical path:** Option 2 (Inpainting + Flux). LoRA — Phase 2 only.
2. **Revenue model:** B2B per-lead (primary). B2C packs (funnel).
3. **Free tier:** 1 generation with watermark.
4. **B2C pricing (RUB):** Mini 149₽ (5), Main 499₽ (20), Extended 899₽ (50).
5. **B2B pricing:** 500–1,500₽/lead → widget 5–15K₽/mo (Phase 2) → SaaS (Phase 3).
6. **Positioning:** patient acquisition engine, NOT dentist-side tool. SmileVision exists (168+ clinics, B2B). Never say "zero competitors" / "first in CIS." Say: "early-stage market; no dominant B2C→B2B lead-gen platform in CIS."
7. **Lead principle (v1.1):** 1 lead = 1 clinic chosen by the user. No lead resale (anti-Fixmysmile differentiation).
8. **Medical disclaimer:** every result screen — "визуальная симуляция, не медицинская рекомендация."
9. **Data privacy:** 152-ФЗ. Consent before first upload. Originals auto-delete after 30 days.
10. **v1.1 MVP scope additions (locked in):** live photo pre-check; action-locked paywall + generation theater; cost-estimate block; branded result delivery. Total +6.5 dev-days, absorbed in Phases 2–5.
11. **Video simulation:** OUT of MVP. Roadmap month 2 after Fal.ai image-to-video cost spike.

---

## Competitive Context (updated 02.07.2026)

| Competitor | Market | Model | Our angle |
|-----------|--------|-------|-----------|
| SmileVision | Russia | B2B SaaS для врачей, 3–30K₽/mo, фото 100₽/видео 500₽; money-back 30 дней | Мы приводим пациента В клинику; они конвертируют уже пришедшего |
| **Fixmysmile.ai** (new) | USA | B2C free simulator + cost estimates → clinic-paid leads. **Наша категория, валидирована в US** | CIS не занят; их слабость — перепродажа лидов «multiple partners» → наш принцип 1 лид = 1 клиника |
| Teethsi | Global/RU | B2C app; **1.2★ Google Play**, «invalid image» failures; Persist Ventures app factory | Урок: качество первой генерации решает всё → наш live pre-check |
| SmileViz | USA | B2B $299–399/mo; QR self-simulation в приёмной | Not in CIS; нет B2C воронки |
| Dentrino (new) | USA | Chairside iPad app + Engage widget | B2B only, нет consumer-канала |
| denta.bot / SmileFy / Simmetry | UK/US | Widgets, video (AVA), lead capture | Not in CIS |

**Positioning statement:** «SmileViz-качество по цене в 2–3 раза ниже, с B2C-воронкой как встроенным генератором спроса для клиник».

**Category status:** модель B2C→B2B валидирована глобально (Fixmysmile, US); в СНГ категория не занята — окно открыто, часы копирования тикают.

---

## ML Pipeline Essentials

### Live Pre-Check (v1.1, on-device, advisory)
| Check | Condition | RU hint |
|---|---|---|
| Face | 1 frontal face, yaw/pitch ±15° | «Повернитесь к камере анфас» |
| Mouth | landmarks present, lips separated | «Улыбнитесь, покажите зубы» |
| Light | face-region brightness ≥ threshold | «Нужно больше света» |
| Sharpness | Laplacian variance ≥ threshold | «Держите телефон ровно» |
| Distance | face bbox 30–70% of frame height | «Подойдите ближе / отойдите» |

Server validation stays authoritative. Blocks → `precheck_blocked(reason)`.

### Mouth Mask (MediaPipe Face Mesh, 468 landmarks)
- Outer lip: 0, 267, 269, 270, 409, 291, 375, 321, 405, 314, 17, 84, 181, 91, 146, 61, 185, 40, 39, 37
- Inner lip: 78, 95, 88, 178, 87, 14, 317, 402, 318, 324, 308, 415, 310, 311, 312, 13, 82, 81, 80, 191
- Fill outer contour → dilate 15–20px → Gaussian blur σ5–8. Sharp edges = «pasted-in» = провал.

### Prompt Templates
| Style | Prompt |
|-------|--------|
| Natural White | Beautiful naturally white teeth, slight improvement in alignment, same lip shape and skin tone, photorealistic, maintain original lighting and shadows |
| Straight Smile | Perfectly aligned straight teeth, natural white shade, no gaps, same lip shape, photorealistic dental result, maintain skin texture |
| Veneer Effect | Professional dental veneer result, uniform tooth shape and size, bright white but natural-looking, celebrity-quality smile, same lip contour |
| Hollywood Smile | Brilliant white Hollywood smile, perfect symmetry, gleaming teeth, red carpet ready, maintain natural lip shape and facial features |

### Provider Abstraction
```python
async def generate(image: bytes, mask: bytes, prompt: str, config: ProviderConfig) -> GenerationResult:
    # returns: result_image, cost_usd, duration_ms
```
Implementations: `MockProvider` (default, returns fixture), `FalProvider` (FLUX.1 Pro Fill, `fal-ai/flux-pro/v1/fill`, $0.05/MP, active when FAL_API_KEY set).

---

## UX Rules (v1.1)

- Live pre-check on camera замещает статичные подсказки; кнопка гейтится до валидного кадра.
- Paywall — action-locked: 2-я генерация / снятие водяного знака / сохранение. Никогда по таймеру. Бенчмарк 16.5% vs 2.1%.
- Generation theater: ожидание 5–15с = аргумент продажи (staged messages + social proof), не спиннер.
- Cost anchor на результате: эмоция → практическое намерение → квалифицированный лид.
- Watermark нельзя обрезать; «Убрать водяной знак» → paywall.
- «Найти клинику» — на каждом экране результата. Видно, не агрессивно.
- Outcome-копирайт: «твоя голливудская улыбка», не «AI-обработка».

---

## Development Phases (v1.1)

| Phase | Scope | Timeline |
|-------|-------|----------|
| 0: Spike | 10 селфи на Fal.ai playground (нужен ключ). No code. | 2–3 дня |
| 1: Skeleton | Monorepo, Flutter shell (16 screens + nav), FastAPI skeleton, миграции 8 таблиц, docker-compose, CI | Week 1–2 |
| 2: Pipeline | Face Mesh + mask + provider abstraction + **live pre-check** + e2e generation (mock) | Week 2–3 |
| 3: Monetization | Packs, limits, watermark, **action-locked paywall + theater**, **cost-estimate block**, YooKassa (mock flag), webhook verify + idempotency | Week 3–4 |
| 4: Quality | 30-selfie harness + scorecard, SSIM check, error handling, Sentry | Week 4–5 |
| 5: B2B | Clinics seed, find-clinic, lead form, clinic notify (email), **branded result delivery** | Week 5–6 |
| 6: Launch | Store submission, closed beta, partner demo | Week 6–7 |

Quality gate: average ≥3.5/5 по 5 критериям (реализм зубов, сохранение лица, стыковка границ, точность стиля, эмоция), ни один <2.0.

---

## Source Discipline

| Type | Rule |
|------|------|
| Verified facts | Официальные сайты/сторы — можно как факт с источником |
| Vendor claims | ROI/конверсии конкурентов — помечать «vendor claim» |
| Team estimates | SAM/SOM, юнит-экономика — помечать «team estimate» |
| Assumptions | Конверсии, willingness to pay — «assumption to validate». НИКОГДА как факт |

---

## Working Rules for Claude

1. **Language:** русский вопрос → русский ответ. Код → English.
2. **No re-litigation:** locked decisions не пересматривать без явного запроса.
3. **Review protocol (= глобальная настройка Селены):** любой содержательный текст/задача/промпт — (1) согласие/несогласие с аргументами обеих сторон, (2) оценка 1–5, (3) до 3 критических недостатков, (4) ревизия. ≥4.5 без критических дефектов → фиксирую одной строкой и выполняю сразу. Ниже → жду одобрения. Не применяется к подтверждениям, уточнениям, бытовым репликам.
4. **Source honesty:** не выдумывать факты; не уверен — скажи; отделяй оценки от фактов.
5. **Competitive honesty:** SmileVision и Fixmysmile существуют. Формула: «категория не занята в СНГ», не «конкурентов нет».
6. **Medical:** «визуализация», не «диагноз» — во всех user-facing текстах.
7. **Header:** каждое сообщение начинается с `DD.MM.YYYY | HH:MM | Bali`.
8. **Files:** дата/время/место в шапке или подвале каждого документа.
9. **Tone:** умный друг, прямо, без лести. Плохая идея → почему + вариант лучше.

---

## Engineering Rules for Claude Code (v1.1)

### Repo layout
```
/app        Flutter (lib/features/<feature>/{ui,state,data})
/backend    FastAPI (app/{api,core,ml,services}, tests/)
/supabase   migrations/*.sql (Supabase-compatible), seed/
/docs       Architecture_v1.1, Brief_v2.6, this file
/scripts    quality harness, batch scoring
SETUP.md    everything Selena must do manually
BLOCKERS.md running log of environment blockers
```

### Commands (must stay green)
- Flutter: `flutter analyze` (0 issues), `flutter test`
- Backend: `ruff check .`, `mypy app`, `pytest`
- One-shot: `make check` runs all of the above

### Environment & mocks — NEVER invent credentials
- All secrets via env; commit `.env.example` only.
- `MOCK_INFERENCE=true` (default): MockProvider returns deterministic fixture result.
- `MOCK_AUTH=true` (default): local JWT stub until Supabase creds.
- `MOCK_PAYMENTS=true` (default): YooKassa flow simulated; webhook handler still real (signature verify + idempotency), tested with fixtures.
- Missing secret → `.env.example` entry + `TODO(SELENA)` comment + line in SETUP.md. Never fake a key, URL, or account.

### Discipline
- Conventional commits; one logical change per commit; never commit secrets or binaries >1MB.
- Fixtures: programmatically generated placeholder face images only; real selfies come from Selena later.
- Blocked >2 attempts on environment issue → log in BLOCKERS.md, switch to next independent task.
- **Stop points:** end of Phase 1 and Phase 2 → STOP, write PHASE_REPORT.md (what built, how to run, what's mocked, open questions), wait for approval.
- DoD for the full run: `make check` green; mock user journey works end-to-end: onboarding → login(mock) → upload(fixture) → style → theater → result with watermark → paywall on 2nd gen → cost block → find clinic (seed) → lead form → lead row in DB + notification logged.

---

## Key Documents

| Document | Version | Purpose |
|----------|---------|---------|
| Partner Brief | v2.6 | Партнёрские встречи |
| Architecture Spec | v1.1 | Полная спека для разработки |
| CLAUDE.md | v1.1 | Этот файл — конституция проекта |
| AGENT_PROMPT.md | v1.0 | Kickoff-промпт для Claude Code agent loop |

## Contacts

- **Selena** — Founder. Все решения через неё.
- **Partner** — TBD (Russia/Uzbekistan).
- **Developer** — Claude Code (agent) + human review.

## Next Actions

1. ☐ Init GitHub repo, положить CLAUDE.md + /docs
2. ☐ Запустить Claude Code с AGENT_PROMPT.md → Phase 1 → stop point → review
3. ☐ Селена: Supabase-проект (URL + anon/service keys), Fal.ai key, 20–30 тестовых селфи
4. ☐ Phase 0 spike на Fal.ai playground (как только есть ключ)
5. ☐ Партнёрская встреча с Brief v2.6
