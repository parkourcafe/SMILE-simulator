# SESSION_HANDOFF — состояние проекта и следующие шаги
> 02.07.2026 | Bali | автор: Claude Code (сессия v1.1 + hero-site)
> Для нового чата: прочитай CLAUDE.md (конституция), затем этот файл, затем продолжай с «Следующие шаги».

## Ссылки

| Что | Где |
|---|---|
| Живой сайт (hero) | https://parkourcafe.github.io/SMILE-simulator/ |
| Репозиторий | github.com/parkourcafe/SMILE-simulator (main — рабочая ветка деплоя) |
| Supabase проект | `htclwrotnmhtbrdisqcu` (https://htclwrotnmhtbrdisqcu.supabase.co) |
| Деплой сайта | GitHub Pages из ветки `gh-pages`; workflow `.github/workflows/deploy-pages.yml` публикует `web/` при пуше в main |
| CI | `.github/workflows/ci.yml` — ruff+pytest (backend) + flutter analyze (app). Зелёный. |

## Состояние (что готово)

- **Бэкенд** (`backend/`): FastAPI, ML-пайплайн (MediaPipe Tasks + маска рта + провайдеры), mock-first: `MOCK_INFERENCE/AUTH/PAYMENTS=true` по умолчанию — всё работает без ключей. 30 тестов зелёные, `make check` проходит.
- **Приложение** (`app/`): Flutter, 16 экранов, v1.1-фичи: generation theater, action-locked paywall, cost-anchor, live pre-check (advisory-заглушка, контракт готов), before/after слайдер. `flutter analyze` зелёный в CI.
- **База** (Supabase): 8 таблиц + сиды (4 стиля, 10 клиник, price_estimates на 3 города). Миграции 0001–0007 применены. **0008 (waitlist + clinic_applications) — в репо, НЕ применена.**
- **Hero-сайт** (`web/index.html`): тёмный кинематографичный, AIDA, 3 AI-видео + 4 AI-фото (славянская внешность, честные дисклеймеры), формы «Ранний доступ» + «Клиника-партнёр».
- **Phase 0** (спайк качества FLUX): 10 селфи готовы и валидированы, скрипт `scripts/phase0/run_spike.py` готов. НЕ прогнан по-настоящему — облако блокирует fal.run, нужен локальный запуск.

## Известные ограничения окружения

- Облачный контейнер блокирует исходящие: `fal.run`, CDN Higgsfield/CloudFront, `github.io`, `vercel.com`. Не пытаться качать оттуда — это политика, не баг.
- Медиа сайта захостлинканы с CDN генератора — TODO: скачать 4 файла и закрепить в `web/assets/` (может истечь ссылка).
- Мёрдж PR через GitHub MCP один раз взял устаревшую точку ветки (PR #1) — после мёрджа ВСЕГДА проверять `get_file_contents` на main, что ключевые файлы легли.

## Следующие шаги (по приоритету)

1. **Формы → база**: после реконнекта Supabase-коннектора применить `supabase/migrations/0008_waitlist.sql`, взять publishable/anon key, вписать в константы `SUPABASE_URL`/`SUPABASE_ANON_KEY` в начале `<script>` в `web/index.html`, запушить в main (Pages обновится сам). Сейчас формы работают через mailto-fallback на parkourcafe@gmail.com.
2. **Phase 0 спайк (Go/No-Go)**: Селена запускает локально на Mac: `cd smile-simulator/backend && pip install -e ".[ml]" && export FAL_API_KEY=<её ключ> && cd ../scripts/phase0 && python3 run_spike.py --input ~/phase0_selfies --output ~/phase0_out --styles natural_white`. Гейт: средний ≥3.5/5, ни один критерий <2.0.
3. **Railway деплой бэкенда** → реальные генерации из приложения (`MOCK_INFERENCE=false` + FAL_API_KEY в env).
4. **Медиа в репо**: скачать 4 ассета (URL в web/index.html) → `web/assets/` (пометить исключение из правила «no binaries >1MB» для маркетинговых ассетов).
5. **Цены**: значения в `price_estimates` — team estimates; заменить на данные клиник до партнёрских встреч.
6. **Юридическое**: политика конфиденциальности + оферта (в футере сайта «в подготовке» — release blocker).

## Секреты (никогда не коммитить)

- FAL_API_KEY — у Селены (выдавался в чате, хранить в `.env` локально / Railway env).
- Supabase service-role / JWT secret — в дашборде проекта, серверная сторона only.
- Публичный anon key — МОЖНО в web/index.html (он для того и создан).

## Рабочие правила сессии (сверх CLAUDE.md)

- Ветка разработки: `claude/*` (текущая: claude/new-session-py5jz5); в main — только через PR + мёрдж + проверка файлов на main.
- Header каждого сообщения Селене: `DD.MM.YYYY | HH:MM | Bali`, язык — русский.
- Генерация медиа — Higgsfield MCP (kling3_0 видео / soul_2 + nano_banana_pro фото); показывать через job_display; без читаемого текста в кадре; всегда дисклеймер «AI-визуализация, не клинический результат».
