# SESSION_HANDOFF — состояние проекта и следующие шаги
> 02.07.2026 | Bali | автор: Claude Code (сессия v1.1 + hero-site)
> Updated: 07.07.2026 | 12:39 | Bali | Codex (forms prepared, media pinned locally)
> Updated: 08.07.2026 | 05:14 | Bali | Codex (premium website pass: typography, hero, editorial sections, mobile polish)
> Updated: 10.07.2026 | 09:35 | Bali | Codex (ZubiLook RU/EN/UZ site deployed to Vercel production on zubilook.com)
> Updated: 10.07.2026 | 14:37 | Bali | Codex (web synchronized, forms schema merged, Phase 0/backend production gates prepared)
> Для нового чата: прочитай CLAUDE.md (конституция), затем этот файл, затем продолжай с «Следующие шаги».

## Ссылки

| Что | Где |
|---|---|
| Живой сайт (основной домен) | https://www.zubilook.com/ (`https://zubilook.com/` редиректит на `www`) |
| Legacy hero URL | https://parkourcafe.github.io/SMILE-simulator/ |
| Репозиторий | github.com/parkourcafe/smile-simulator |
| Supabase проект | `htclwrotnmhtbrdisqcu` (https://htclwrotnmhtbrdisqcu.supabase.co) |
| Деплой сайта | Vercel project `yulaboober/smile-simulator`; `vercel.json` публикует `web/` как output directory |
| CI | `.github/workflows/ci.yml` — ruff+pytest (backend) + flutter analyze (app). Зелёный. |
| Детальный релизный план | `docs/AGENT_LOOP_PLAN.md` — гейты от форм до закрытой beta и решения по сторам. |

## Состояние (что готово)

- **Бэкенд** (`backend/`): FastAPI, ML-пайплайн (MediaPipe Tasks + маска рта + провайдеры), mock-first: `MOCK_INFERENCE/AUTH/PAYMENTS=true` по умолчанию — всё работает без ключей. 43 теста зелёные, `make check` проходит.
- **Приложение** (`app/`): Flutter, 16 экранов, v1.1-фичи: generation theater, action-locked paywall, cost-anchor, live pre-check (advisory-заглушка, контракт готов), before/after слайдер. `flutter analyze` зелёный в CI.
- **База** (Supabase): 8 таблиц + сиды (4 стиля, 10 клиник, price_estimates на 3 города). Миграции 0001–0007 применены. **Расширенная 0008 (waitlist + clinic_applications + версия/время согласия) — в `main`, НЕ применена.**
- **Hero-сайт** (`web/index.html`): бренд ZubiLook, RU/EN/UZ переключатель, тёмный кинематографичный, AIDA, 2 AI-видео + 4 AI-фото (AI-визуализация, честные дисклеймеры), формы «Ранний доступ» + «Клиника-партнёр». Premium-pass применён: Cormorant Garamond + Onest, product-first hero, editorial timeline/ledger вместо части card grids, mobile hero rules, локальные медиа в `web/assets/`. Production deploy на Vercel: `https://www.zubilook.com/`. Формы подготовлены к Supabase REST, но `SUPABASE_ANON_KEY` ещё пустой до применения `0008`.
- **Phase 0** (спайк качества FLUX): скрипт `scripts/phase0/run_spike.py`, scorecard и реальный MediaPipe CPU-путь готовы; локальный smoke прошёл с `face_approximate=false`. Настоящий Go/No-Go НЕ проведён: нужно повторно указать папку ровно с 10 согласованными селфи и установить локальный `FAL_API_KEY`.
- **Backend security gate**: PR #9 слит. Supabase Auth поддерживает ES256/RS256 JWKS с legacy HS256 fallback и новые publishable/secret keys; wildcard CORS закрыт; production-старт с mock auth/default admin key запрещён. CI зелёный.

## Известные ограничения окружения

- Среда ограничивает исходящие подключения. GitHub/Vercel проверяются утверждёнными инструментами; `fal.run` для Phase 0 запускать локально. Supabase в этой сессии подключать через коннектор, не обходить сетевые ограничения.
- Медиа сайта больше не зависят от CDN генератора: файлы закреплены в `web/assets/`. Исключение для видео >1MB описано в `web/assets/README.md`.
- Мёрдж PR через GitHub MCP один раз взял устаревшую точку ветки (PR #1) — после мёрджа ВСЕГДА проверять `get_file_contents` на main, что ключевые файлы легли.

## Следующие шаги (по приоритету)

1. **Формы → база**: после реконнекта Supabase-коннектора применить `supabase/migrations/0008_waitlist.sql`, взять publishable/anon key, вписать в `SUPABASE_ANON_KEY` в начале `<script>` в `web/index.html`, затем сделать production deploy на Vercel. Проверить одну B2C и одну B2B заявку, consent metadata и запрет anon read/update/delete. `SUPABASE_URL` уже вписан; пока key пустой, формы работают через mailto-fallback на parkourcafe@gmail.com.
2. **Phase 0 спайк (Go/No-Go)**: Селена запускает локально на Mac: `cd smile-simulator/backend && pip install -e ".[ml]" && export FAL_API_KEY=<её ключ> && cd ../scripts/phase0 && python3 run_spike.py --input ~/phase0_selfies --output ~/phase0_out --styles natural_white`. Гейт: средний ≥3.5/5, ни один критерий <2.0.
3. **Railway деплой бэкенда** → реальные генерации из приложения (`MOCK_INFERENCE=false` + FAL_API_KEY в env).
4. **Цены**: значения в `price_estimates` — team estimates; заменить на данные клиник до партнёрских встреч.
5. **Юридическое**: политика конфиденциальности + оферта (в футере сайта «в подготовке» — release blocker).

Полная последовательность, входные зависимости и exit evidence: `docs/AGENT_LOOP_PLAN.md`.

## Секреты (никогда не коммитить)

- FAL_API_KEY — у Селены (выдавался в чате, хранить в `.env` локально / Railway env).
- Supabase secret/service-role key и legacy JWT secret — в дашборде проекта, серверная сторона only.
- Публичный publishable/anon key — МОЖНО в `web/index.html` и Flutter-клиенте.

## Рабочие правила сессии (сверх CLAUDE.md)

- Ветки разработки: `claude/*`; в main — только через PR + мёрдж + проверка файлов на main.
- Header каждого сообщения Селене: `DD.MM.YYYY | HH:MM | Bali`, язык — русский.
- Генерация медиа — Higgsfield MCP (kling3_0 видео / soul_2 + nano_banana_pro фото); показывать через job_display; без читаемого текста в кадре; всегда дисклеймер «AI-визуализация, не клинический результат».
