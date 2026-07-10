# SESSION_HANDOFF — состояние проекта и следующие шаги
> 02.07.2026 | Bali | автор: Claude Code (сессия v1.1 + hero-site)
> Updated: 07.07.2026 | 12:39 | Bali | Codex (forms prepared, media pinned locally)
> Updated: 08.07.2026 | 05:14 | Bali | Codex (premium website pass: typography, hero, editorial sections, mobile polish)
> Updated: 10.07.2026 | 09:35 | Bali | Codex (ZubiLook RU/EN/UZ site deployed to Vercel production on zubilook.com)
> Updated: 10.07.2026 | 14:37 | Bali | Codex (web synchronized, forms schema merged, Phase 0/backend production gates prepared)
> Updated: 10.07.2026 | 18:55 | Bali | Codex (OTP/leads/retention and Railway production image merged; legal drafts preserved)
> Updated: 10.07.2026 | 20:10 | Bali | Codex (verified photo-deletion UI merged; Phase 0 evidence workflow hardened)
> Updated: 10.07.2026 | 16:33 | Bali | Codex (OTP profile provisioning and pre-upload photo consent prepared)
> Updated: 10.07.2026 | 16:38 | Bali | Codex (atomic generation quota and migration smoke prepared)
> Updated: 10.07.2026 | 17:09 | Bali | Codex (real YooKassa flow and server entitlements prepared)
> Для нового чата: прочитай CLAUDE.md (конституция), затем этот файл, затем продолжай с «Следующие шаги».

## Ссылки

| Что | Где |
|---|---|
| Живой сайт (основной домен) | https://www.zubilook.com/ (`https://zubilook.com/` редиректит на `www`) |
| Legacy hero URL | https://parkourcafe.github.io/SMILE-simulator/ |
| Репозиторий | github.com/parkourcafe/smile-simulator |
| Supabase проект | `htclwrotnmhtbrdisqcu` (https://htclwrotnmhtbrdisqcu.supabase.co) |
| Деплой сайта | Vercel project `yulaboober/smile-simulator`; `vercel.json` публикует `web/` как output directory |
| CI | `.github/workflows/ci.yml` — database migrations/invariants + backend lint/test + production Docker smoke + Flutter analyze/test. Зелёный на `main`; текущие payment-изменения ждут PR CI. |
| Детальный релизный план | `docs/AGENT_LOOP_PLAN.md` — гейты от форм до закрытой beta и решения по сторам. |
| Юридический release gate | `docs/legal/LEGAL_RELEASE_GATE.md` + непубликуемые черновики policy/terms. |

## Состояние (что готово)

- **Бэкенд** (`backend/`): FastAPI, ML-пайплайн, современная Supabase JWT/key-поддержка, idempotent leads, retryable hard deletion + 30-day retention job. 106 тестов зелёные локально. Production Railway image запускается non-root, использует dynamic `PORT`, pinned dependency lock и проверенный Face Landmarker; `/health` и dependency-aware `/ready` покрыты CI. Серверный photo-consent receipt создаётся до выдачи Storage-path. Атомарный quota RPC резервирует credit до inference и освобождает его при failure/deletion. YooKassa create/get использует Basic Auth + idempotency; webhook и status recovery сверяются server-to-server и активируют pack атомарным RPC. Payment PR ещё ждёт GitHub CI и test-shop E2E.
- **Приложение** (`app/`): Flutter, реальные Supabase phone OTP request/verify/session guards, список активных клиник из API, отдельное согласие + UUID idempotency для одного лида на одну клинику и отдельное согласие до загрузки каждого фото. Entitlements теперь загружаются с backend; premium styles и новый запуск гейтятся серверным остатком. Checkout открывает реальный URL и не выдаёт pack до подтверждённого payment status. Локальный mock OTP остаётся только без production config; payment Flutter changes ждут CI и device E2E.
- **База** (Supabase): numbered migrations `0001`–`0014` подготовлены. `0008` добавляет waitlist/clinic applications + consent metadata, `0009` — photo retention/tombstones, `0010` — lead consent/security/idempotency, `0011` — provisioning `public.users` после Auth OTP, `0012` — photo-processing receipts + Storage RLS, `0013` — atomic quota, `0014` — durable YooKassa intents + one-payment/one-pack activation. На чистом PostgreSQL 16 локально прошли весь migration chain, behavioral SQL assertions, повторная payment activation и две конкурентные reservation-сессии. Удалённое состояние сейчас не проверено; `0008`–`0014` нельзя считать применёнными до проверки через Supabase-коннектор. `seed_dev.sql` запрещён для production.
- **Hero-сайт** (`web/index.html`): бренд ZubiLook, RU/EN/UZ переключатель, тёмный кинематографичный, AIDA, 2 AI-видео + 4 AI-фото (AI-визуализация, честные дисклеймеры), формы «Ранний доступ» + «Клиника-партнёр». Premium-pass применён: Cormorant Garamond + Onest, product-first hero, editorial timeline/ledger вместо части card grids, mobile hero rules, локальные медиа в `web/assets/`. Production deploy на Vercel: `https://www.zubilook.com/`. Формы подготовлены к Supabase REST, но `SUPABASE_ANON_KEY` ещё пустой до применения `0008`.
- **Phase 0** (спайк качества FLUX): preflight требует clean commit, ровно 10 уникальных consented inputs, срок удаления <=30 дней, один стиль и реальный CPU Face Landmarker. Run фиксирует config/request IDs/checksums; `evaluate_scorecard.py` формирует проверяемый GO/ITERATE/NO-GO и не принимает dry-run как evidence. Fal payload синхронизирован с официальной Fill schema; 1024x1024 оценивается в $0.10 из-за округления до 2 MP. Настоящий Go/No-Go НЕ проведён: нет папки с 10 согласованными селфи и локального `FAL_API_KEY`.
- **Backend release gates**: PR #9 (auth/config), #11 (photo retention), #13 (lead security), #14 (Flutter clinic lead path), #15 (Railway image/readiness), #19 (pre-upload consent) и #20 (atomic quota) слиты. `APP_ENV=production` запрещает mocks, неверную модель, отсутствующие credentials, unsafe CORS и отсутствие канала уведомления клиники.
- **Юридическое**: `docs/legal/` содержит release checklist и canonical EN drafts. Они не публикуются, пока не подтверждены оператор, адрес, юрисдикция, email, география beta, processor regions и regulator status.

## Известные ограничения окружения

- Среда ограничивает исходящие подключения. GitHub/Vercel проверяются утверждёнными инструментами; `fal.run` для Phase 0 запускать локально. Supabase в этой сессии подключать через коннектор, не обходить сетевые ограничения.
- Медиа сайта больше не зависят от CDN генератора: файлы закреплены в `web/assets/`. Исключение для видео >1MB описано в `web/assets/README.md`.
- Мёрдж PR через GitHub MCP один раз взял устаревшую точку ветки (PR #1) — после мёрджа ВСЕГДА проверять `get_file_contents` на main, что ключевые файлы легли.

## Следующие шаги (по приоритету)

1. **Supabase + формы**: после реконнекта коннектора проверить migration history и данные, затем применить `0008`–`0014` по порядку (перед `0010` проверить lead-дубли, перед `0013` — quota preflight из `SETUP.md`). Проверить Auth backfill, consent grants, quota RPC и payment activation RPC. Взять publishable/anon key, вписать его в `web/index.html`, задеплоить Vercel. Проверить реальные B2C/B2B заявки и запрет anon read/update/delete.
2. **Phase 0 спайк (Go/No-Go)**: подготовить clean worktree, 10 pseudonymous selfies и `consent_manifest.csv` по `scripts/phase0/README.md`; установить `FAL_API_KEY` только в env и запустить `python scripts/phase0/run_spike.py --input ~/phase0_selfies --output ~/phase0_run_v1 --styles natural_white`. После слепой оценки запустить `evaluate_scorecard.py`. Гейт: 10/10, средний ≥3.5/5, каждый критерий ≥2.0, без recurring identity failure.
3. **Юридическое**: получить реквизиты из `docs/legal/LEGAL_RELEASE_GATE.md`, подтвердить реальные регионы/процессоры и legal review; затем выпустить RU/EN/UZ страницы и заменить футер/ссылки согласия. Это release blocker.
4. **Railway staging**: Root Directory `/backend`, config `/backend/railway.json`; внести secrets и проверить `/health` + `/ready` только после миграций. Добавить daily retention cron и five-minute quota reconciliation cron. Production promotion — после Phase 0 GO, legal gate, approved clinic и real OTP/lead smoke.
5. **Реальный mobile E2E**: включить Supabase Phone Auth/SMS provider/rate limits/CAPTCHA, собрать Flutter с publishable key + Railway API URL, проверить OTP → profile → consent → upload → generation → clinic → lead → delete/retention. Payment E2E проводить отдельно в YooKassa test shop до любых реальных списаний.
6. **Цены**: значения в `price_estimates` — team estimates; заменить на подтверждённые данные клиник до партнёрских встреч.

Полная последовательность, входные зависимости и exit evidence: `docs/AGENT_LOOP_PLAN.md`.

## Секреты (никогда не коммитить)

- FAL_API_KEY — отсутствует в текущем окружении; получить из Fal.ai dashboard и хранить только локально / в Railway secret env.
- Supabase secret/service-role key и legacy JWT secret — в дашборде проекта, серверная сторона only.
- Публичный publishable/anon key — МОЖНО в `web/index.html` и Flutter-клиенте.

## Рабочие правила сессии (сверх CLAUDE.md)

- Ветки разработки: `codex/*` (старые `claude/*` допустимы); в main — только через PR + мёрдж + проверка файлов на main.
- Header каждого сообщения Селене: `DD.MM.YYYY | HH:MM | Bali`, язык — русский.
- Генерация медиа — Higgsfield MCP (kling3_0 видео / soul_2 + nano_banana_pro фото); показывать через job_display; без читаемого текста в кадре; всегда дисклеймер «AI-визуализация, не клинический результат».
