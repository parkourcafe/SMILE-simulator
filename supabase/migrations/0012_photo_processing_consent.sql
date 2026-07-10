-- Server-issued consent receipts prove that processing consent was recorded before
-- the client received the private Storage path for a selfie.

create table photo_processing_consents (
  id                uuid primary key,
  user_id           uuid not null references users(id) on delete cascade,
  consent_given     boolean not null check (consent_given),
  consent_version   text not null check (length(trim(consent_version)) between 1 and 80),
  consent_locale    text not null check (consent_locale in ('ru', 'en', 'uz')),
  consent_scope     text not null default 'smile_visualization'
    check (consent_scope = 'smile_visualization'),
  photo_object_path text not null unique,
  consented_at      timestamptz not null,
  created_at        timestamptz not null default now(),
  constraint photo_processing_consents_path_matches_receipt check (
    photo_object_path = user_id::text || '/' || id::text || '_original'
  )
);

create index photo_processing_consents_user_time_idx
  on photo_processing_consents (user_id, consented_at desc);

alter table photo_processing_consents enable row level security;

-- Receipts are created and validated only by the API gateway. Mobile clients get
-- the receipt through the authenticated API and cannot forge or rewrite one via REST.
revoke all on photo_processing_consents from anon, authenticated;

alter table generations
  add column photo_consent_id uuid
    references photo_processing_consents(id) on delete set null;

create index generations_photo_consent_idx
  on generations (photo_consent_id)
  where photo_consent_id is not null;

-- Storage itself enforces the receipt, so a modified client cannot bypass the API
-- sequence and upload an arbitrary selfie under its user folder.
create or replace function public.can_upload_consented_photo(object_name text)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1
    from public.photo_processing_consents as consent
    where consent.user_id = (select auth.uid())
      and consent.consent_given
      and consent.consent_version = 'photo-beta-2026-07-10'
      and consent.consent_scope = 'smile_visualization'
      and consent.photo_object_path = object_name
  );
$$;

revoke all on function public.can_upload_consented_photo(text) from public;
grant execute on function public.can_upload_consented_photo(text) to authenticated;

drop policy if exists "photos_owner_rw" on storage.objects;

create policy "photos_owner_select" on storage.objects
  for select to authenticated
  using (bucket_id = 'photos' and (storage.foldername(name))[1] = auth.uid()::text);

create policy "photos_consented_insert" on storage.objects
  for insert to authenticated
  with check (
    bucket_id = 'photos'
    and public.can_upload_consented_photo(name)
  );

create policy "photos_consented_update" on storage.objects
  for update to authenticated
  using (
    bucket_id = 'photos'
    and public.can_upload_consented_photo(name)
  )
  with check (
    bucket_id = 'photos'
    and public.can_upload_consented_photo(name)
  );
