# AI Smile Simulator — Flutter client

iOS + Android client. Single codebase (CLAUDE.md Tech Stack). State via Riverpod,
navigation via `go_router`, backend via the API gateway + Supabase Auth.

> This is a **skeleton**: routes, theme, API client, providers, and screen stubs for
> all 16 screens (CLAUDE.md → Screen Map). Screens render placeholder UI and are
> marked `// TODO(phase-N)` where real widgets/logic go. The inference API is never
> called from here — only the gateway (`ApiClient`).

## Run

```bash
flutter pub get
flutter run \
  --dart-define=API_BASE_URL=http://localhost:8000/v1 \
  --dart-define=SUPABASE_URL=https://your-project.supabase.co \
  --dart-define=SUPABASE_ANON_KEY=your-anon-key
```

## Layout

```
lib/
  main.dart                 app bootstrap (Supabase init + ProviderScope)
  src/
    config/env.dart         compile-time config (--dart-define)
    theme/app_theme.dart    colors, typography
    router/app_router.dart  go_router routes (16 screens)
    api/                     ApiClient (dio) + DTO models
    providers/               Riverpod providers (auth, styles, generation, clinics)
    features/<screen>/        one folder per screen
```

## Key UX rules baked into routing (CLAUDE.md)

- Paywall comes AFTER the result (peak emotion), never before.
- Watermark on free results cannot be cropped out → "Remove watermark" routes to paywall.
- "Find a clinic" is present on every result screen.
- Medical disclaimer shown on every result screen ("visualization, not diagnosis").
