-- Landing-page capture (AIDA Action blocks): waitlist (B2C) + clinic applications (B2B).
-- Both are inserted directly from the public hero page using the anon key, so RLS
-- allows INSERT only — no anon read-back (service role reads them server-side).

create table waitlist (
  id              uuid primary key default gen_random_uuid(),
  name            text check (name is null or length(trim(name)) between 1 and 120),
  contact         text not null check (length(trim(contact)) between 5 and 200),
  city            text check (city is null or length(trim(city)) between 1 and 120),
  interest        text not null default 'app' check (interest in ('app', 'clinic')),
  comment         text check (comment is null or length(trim(comment)) <= 1000),
  locale          text not null check (locale in ('ru', 'en', 'uz')),
  consent_given   boolean not null check (consent_given),
  consent_version text not null check (length(trim(consent_version)) between 1 and 80),
  consented_at    timestamptz not null default now(),
  source          text not null default 'hero' check (source = 'hero'),
  created_at      timestamptz not null default now()
);
-- One signup per contact; the page treats a conflict as "already on the list".
create unique index waitlist_contact_uniq on waitlist (lower(trim(contact)));

alter table waitlist enable row level security;
create policy waitlist_anon_insert on waitlist
  for insert to anon with check (consent_given and source = 'hero');
grant insert on waitlist to anon;

create table clinic_applications (
  id              uuid primary key default gen_random_uuid(),
  clinic_name     text not null check (length(trim(clinic_name)) between 2 and 200),
  city            text check (city is null or length(trim(city)) between 1 and 120),
  phone           text not null check (length(trim(phone)) between 5 and 40),
  contact_person  text check (
    contact_person is null or length(trim(contact_person)) between 1 and 160
  ),
  email           text check (email is null or length(trim(email)) between 3 and 254),
  monthly_flow    text check (monthly_flow is null or length(trim(monthly_flow)) <= 120),
  interest        text not null default 'pilot'
                    check (interest in ('pilot', 'leads', 'partnership')),
  message         text check (message is null or length(trim(message)) <= 2000),
  locale          text not null check (locale in ('ru', 'en', 'uz')),
  consent_given   boolean not null check (consent_given),
  consent_version text not null check (length(trim(consent_version)) between 1 and 80),
  consented_at    timestamptz not null default now(),
  source          text not null default 'hero' check (source = 'hero'),
  created_at      timestamptz not null default now()
);

alter table clinic_applications enable row level security;
create policy clinic_applications_anon_insert on clinic_applications
  for insert to anon with check (consent_given and source = 'hero');
grant insert on clinic_applications to anon;
