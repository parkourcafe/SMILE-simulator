-- Landing-page capture (AIDA Action blocks): waitlist (B2C) + clinic applications (B2B).
-- Both are inserted directly from the public hero page using the anon key, so RLS
-- allows INSERT only — no anon read-back (service role reads them server-side).

create table waitlist (
  id         uuid primary key default gen_random_uuid(),
  contact    text not null check (length(trim(contact)) between 5 and 200),
  city       text,
  source     text not null default 'hero',
  created_at timestamptz not null default now()
);
-- One signup per contact; the page treats a conflict as "already on the list".
create unique index waitlist_contact_uniq on waitlist (lower(trim(contact)));

alter table waitlist enable row level security;
create policy waitlist_anon_insert on waitlist
  for insert to anon with check (true);

create table clinic_applications (
  id             uuid primary key default gen_random_uuid(),
  clinic_name    text not null check (length(trim(clinic_name)) between 2 and 200),
  city           text,
  phone          text not null check (length(trim(phone)) between 5 and 40),
  contact_person text,
  created_at     timestamptz not null default now()
);

alter table clinic_applications enable row level security;
create policy clinic_applications_anon_insert on clinic_applications
  for insert to anon with check (true);
