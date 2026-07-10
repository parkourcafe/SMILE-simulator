-- Lead consent/idempotency and revocable clinic API credentials.

alter table leads
  add column idempotency_key uuid,
  add column transfer_consent_given boolean,
  add column transfer_consent_version text,
  add column transfer_consent_locale text,
  add column transfer_consented_at timestamptz,
  add constraint leads_transfer_consent_complete check (
    (
      transfer_consent_given is null and
      transfer_consent_version is null and
      transfer_consent_locale is null and
      transfer_consented_at is null
    ) or (
      transfer_consent_given is true and
      transfer_consent_version is not null and
      length(trim(transfer_consent_version)) between 1 and 80 and
      transfer_consent_locale is not null and
      transfer_consent_locale in ('ru', 'en', 'uz') and
      transfer_consented_at is not null
    )
  );

-- A visualization can be sent to exactly one clinic. Retries return the existing row.
create unique index leads_user_generation_one_clinic_uniq
  on leads (user_id, generation_id);

create unique index leads_user_idempotency_uniq
  on leads (user_id, idempotency_key)
  where idempotency_key is not null;

create table clinic_api_keys (
  id           uuid primary key default gen_random_uuid(),
  clinic_id    uuid not null references clinics(id) on delete cascade,
  key_hash     text not null unique check (key_hash ~ '^[0-9a-f]{64}$'),
  label        text check (label is null or length(trim(label)) between 1 and 120),
  status       text not null default 'active' check (status in ('active', 'revoked')),
  created_at   timestamptz not null default now(),
  last_used_at timestamptz,
  revoked_at   timestamptz
);

create index clinic_api_keys_clinic_status_idx
  on clinic_api_keys (clinic_id, status);

alter table clinic_api_keys enable row level security;
revoke all on clinic_api_keys from anon, authenticated;
