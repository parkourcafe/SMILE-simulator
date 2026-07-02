-- 8th table (v1.1): price_estimates — powers the result-screen cost anchor
-- ("Такая улыбка в {city}: {range}") and the "learn exact price at a nearby
-- clinic" CTA. City × style × treatment × price range × currency.
--
-- SOURCE DISCIPLINE: every number seeded here is a TEAM ESTIMATE / assumption to
-- validate, NOT a verified fact. Replace with clinic-sourced ranges before any
-- partner-facing use. The `is_estimate` flag is surfaced so the UI can hedge copy.

create table price_estimates (
  id               uuid primary key default gen_random_uuid(),
  city             text not null,                       -- Moscow, SPb, Tashkent
  style_id         uuid references styles(id) on delete cascade,
  treatment_label     text not null,                    -- e.g. "Teeth whitening"
  treatment_label_ru  text not null,                    -- RU UI label
  price_min        numeric(12,2) not null,
  price_max        numeric(12,2) not null,
  currency         text not null default 'RUB',         -- RUB (RU) / UZS (Tashkent)
  is_estimate      boolean not null default true,       -- team estimate until validated
  sort_order       int not null default 0,
  is_active        boolean not null default true,
  created_at       timestamptz not null default now(),
  constraint price_estimates_range_chk check (price_max >= price_min)
);
create index price_estimates_city_style_idx on price_estimates(city, style_id);

-- ---------------------------------------------------------------------------
-- Seed (TEAM ESTIMATE). RU cities in RUB, Tashkent in UZS.
-- ---------------------------------------------------------------------------
insert into price_estimates
  (city, style_id, treatment_label, treatment_label_ru, price_min, price_max, currency, sort_order)
values
  -- Moscow (RUB)
  ('Moscow', (select id from styles where name = 'Natural White'),
   'Professional whitening', 'Профессиональное отбеливание', 8000, 25000, 'RUB', 1),
  ('Moscow', (select id from styles where name = 'Straight Smile'),
   'Clear aligners', 'Элайнеры (капы)', 90000, 250000, 'RUB', 2),
  ('Moscow', (select id from styles where name = 'Veneer Effect'),
   'Veneers (front zone)', 'Виниры (зона улыбки)', 120000, 400000, 'RUB', 3),
  ('Moscow', (select id from styles where name = 'Hollywood Smile'),
   'Full veneer set', 'Полный комплект виниров', 250000, 700000, 'RUB', 4),

  -- Saint Petersburg (RUB, ~10-15% below Moscow — team estimate)
  ('SPb', (select id from styles where name = 'Natural White'),
   'Professional whitening', 'Профессиональное отбеливание', 7000, 22000, 'RUB', 1),
  ('SPb', (select id from styles where name = 'Straight Smile'),
   'Clear aligners', 'Элайнеры (капы)', 80000, 220000, 'RUB', 2),
  ('SPb', (select id from styles where name = 'Veneer Effect'),
   'Veneers (front zone)', 'Виниры (зона улыбки)', 100000, 350000, 'RUB', 3),
  ('SPb', (select id from styles where name = 'Hollywood Smile'),
   'Full veneer set', 'Полный комплект виниров', 220000, 600000, 'RUB', 4),

  -- Tashkent (UZS)
  ('Tashkent', (select id from styles where name = 'Natural White'),
   'Professional whitening', 'Профессиональное отбеливание', 500000, 1500000, 'UZS', 1),
  ('Tashkent', (select id from styles where name = 'Straight Smile'),
   'Clear aligners', 'Элайнеры (капы)', 5000000, 15000000, 'UZS', 2),
  ('Tashkent', (select id from styles where name = 'Veneer Effect'),
   'Veneers (front zone)', 'Виниры (зона улыбки)', 8000000, 25000000, 'UZS', 3),
  ('Tashkent', (select id from styles where name = 'Hollywood Smile'),
   'Full veneer set', 'Полный комплект виниров', 15000000, 40000000, 'UZS', 4);
