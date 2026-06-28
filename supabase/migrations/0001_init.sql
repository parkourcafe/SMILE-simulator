-- AI Smile Simulator — initial schema
-- Mirrors architecture spec §3. All tables use UUID PKs and timestamps.
-- Photos are NOT stored in the DB — only signed-URL references to Supabase Storage.

create extension if not exists "pgcrypto";   -- gen_random_uuid()

-- ---------------------------------------------------------------------------
-- Enums
-- ---------------------------------------------------------------------------
create type generation_status as enum ('pending', 'processing', 'completed', 'failed');
create type pack_type         as enum ('mini', 'main', 'extended', 'promo');
create type payment_provider  as enum ('yookassa', 'click', 'payme', 'apple_iap', 'google_play');
create type payment_status    as enum ('pending', 'completed', 'failed', 'refunded');
create type clinic_status     as enum ('active', 'paused', 'trial');
create type lead_status       as enum ('new', 'notified', 'contacted', 'booked', 'completed', 'rejected');

-- ---------------------------------------------------------------------------
-- updated_at trigger helper
-- ---------------------------------------------------------------------------
create or replace function set_updated_at()
returns trigger language plpgsql
set search_path = ''   -- pin search_path (Supabase linter 0011); only uses now()/NEW
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- ---------------------------------------------------------------------------
-- 3.1 users  (id matches Supabase Auth user id)
-- ---------------------------------------------------------------------------
create table users (
  id             uuid primary key references auth.users(id) on delete cascade,
  phone          text,                       -- with country code (+7..., +998...)
  email          text,
  display_name   text,                        -- for clinic-facing lead form
  city           text,                        -- for geo-matching with clinics
  free_gens_used int  not null default 0,     -- free tier usage; max = 1
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now()
);
create trigger users_set_updated_at before update on users
  for each row execute function set_updated_at();

-- ---------------------------------------------------------------------------
-- 3.3 styles  (referenced by generations; created before it for FK)
-- ---------------------------------------------------------------------------
create table styles (
  id              uuid primary key default gen_random_uuid(),
  name            text not null,               -- e.g. "Natural White"
  name_ru         text not null,               -- Russian localization
  prompt_template text not null,               -- template with {variables}
  thumbnail_url   text,
  is_premium      boolean not null default false,
  sort_order      int not null default 0,
  is_active       boolean not null default true,
  created_at      timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- 3.2 generations
-- ---------------------------------------------------------------------------
create table generations (
  id                   uuid primary key default gen_random_uuid(),
  user_id              uuid not null references users(id) on delete cascade,
  original_photo_url   text not null,          -- Supabase Storage signed URL
  result_photo_url     text,                   -- null until completed
  mask_url             text,                   -- stored for debugging/retraining
  style_id             uuid references styles(id),
  status               generation_status not null default 'pending',
  prompt               text,
  inference_provider   text,                   -- fal_flux_pro_fill | replicate_flux | ...
  inference_cost_usd   numeric(6,4),
  inference_duration_ms int,
  quality_score        numeric(3,1),           -- 1.0–5.0
  has_watermark        boolean not null default false,
  error_message        text,
  created_at           timestamptz not null default now()
);
create index generations_user_id_idx on generations(user_id, created_at desc);
create index generations_status_idx  on generations(status);

-- ---------------------------------------------------------------------------
-- 3.4 packs
-- ---------------------------------------------------------------------------
create table packs (
  id                uuid primary key default gen_random_uuid(),
  user_id           uuid not null references users(id) on delete cascade,
  pack_type         pack_type not null,
  generations_total int not null,              -- 5, 20, 50 depending on pack
  generations_used  int not null default 0,
  price_amount      numeric(8,2) not null,     -- 149, 499, 899 (RUB)
  price_currency    text not null,             -- RUB, UZS, USD
  purchased_at      timestamptz not null default now(),
  expires_at        timestamptz
);
create index packs_user_id_idx on packs(user_id);

-- ---------------------------------------------------------------------------
-- 3.5 payments
-- ---------------------------------------------------------------------------
create table payments (
  id                  uuid primary key default gen_random_uuid(),
  user_id             uuid not null references users(id) on delete cascade,
  pack_id             uuid references packs(id),
  amount              numeric(10,2) not null,
  currency            text not null,           -- RUB, UZS, USD
  provider            payment_provider not null,
  provider_payment_id text not null,           -- external id for reconciliation
  status              payment_status not null default 'pending',
  created_at          timestamptz not null default now(),
  completed_at        timestamptz,
  -- idempotency: a given external payment id is processed exactly once
  constraint payments_provider_payment_id_uniq unique (provider, provider_payment_id)
);
create index payments_user_id_idx on payments(user_id);

-- ---------------------------------------------------------------------------
-- 3.6 clinics
-- ---------------------------------------------------------------------------
create table clinics (
  id            uuid primary key default gen_random_uuid(),
  name          text not null,
  city          text not null,                 -- Moscow, SPb, Tashkent
  address       text,
  lat           numeric(9,6),
  lng           numeric(9,6),
  phone         text,
  email         text,                          -- for lead notifications
  website       text,
  logo_url      text,
  specialties   text[] not null default '{}',  -- veneers, whitening, implants, ...
  lead_price_rub numeric(8,2) not null default 0,
  status        clinic_status not null default 'trial',
  created_at    timestamptz not null default now()
);
create index clinics_city_idx on clinics(city);

-- ---------------------------------------------------------------------------
-- 3.7 leads
-- ---------------------------------------------------------------------------
create table leads (
  id                  uuid primary key default gen_random_uuid(),
  user_id             uuid not null references users(id) on delete cascade,
  clinic_id           uuid not null references clinics(id),
  generation_id       uuid not null references generations(id),
  user_name           text not null,           -- from lead form
  user_phone          text not null,           -- from lead form
  preferred_time      text,                    -- morning / afternoon / evening
  status              lead_status not null default 'new',
  clinic_notified_at  timestamptz,
  clinic_responded_at timestamptz,
  lead_cost_rub       numeric(8,2) not null default 0,
  created_at          timestamptz not null default now()
);
create index leads_clinic_id_idx on leads(clinic_id, status);
create index leads_user_id_idx   on leads(user_id);
