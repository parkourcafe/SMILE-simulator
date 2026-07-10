-- Reserve a generation credit and create its row in one database transaction.
-- This prevents concurrent requests from spending one free/pack credit more than once.

alter table users
  add constraint users_free_gens_used_nonnegative check (free_gens_used >= 0);

alter table packs
  add constraint packs_generations_total_positive check (generations_total > 0),
  add constraint packs_generations_used_range check (
    generations_used >= 0 and generations_used <= generations_total
  );

alter table generations
  add column quota_source text check (quota_source in ('free', 'pack')),
  add column quota_pack_id uuid references packs(id) on delete restrict,
  add column quota_state text check (quota_state in ('reserved', 'consumed', 'released')),
  add column quota_reserved_at timestamptz,
  add column quota_settled_at timestamptz,
  add column quota_released_at timestamptz,
  add constraint generations_quota_complete check (
    (
      quota_source is null and
      quota_pack_id is null and
      quota_state is null and
      quota_reserved_at is null and
      quota_settled_at is null and
      quota_released_at is null
    ) or (
      quota_source is not null and
      quota_state is not null and
      quota_reserved_at is not null and
      (
        (quota_source = 'free' and quota_pack_id is null and has_watermark) or
        (quota_source = 'pack' and quota_pack_id is not null and not has_watermark)
      ) and
      (
        (quota_state = 'reserved' and quota_settled_at is null and quota_released_at is null) or
        (quota_state = 'consumed' and quota_settled_at is not null and quota_released_at is null) or
        (quota_state = 'released' and quota_settled_at is null and quota_released_at is not null)
      )
    )
  );

create index generations_reserved_quota_idx
  on generations (quota_reserved_at)
  where quota_state = 'reserved';

create or replace function public.reserve_generation_quota(
  p_user_id uuid,
  p_style_id uuid,
  p_photo_consent_id uuid,
  p_original_photo_path text,
  p_rate_limit integer
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  reserved_user public.users%rowtype;
  selected_pack public.packs%rowtype;
  created_generation public.generations%rowtype;
  reserved_at timestamptz := now();
begin
  -- The user lock serializes all quota reservations for one account, including
  -- reservations that compete for different packs or the free credit.
  select * into reserved_user
  from public.users
  where id = p_user_id
  for update;

  if reserved_user.id is null then
    return jsonb_build_object('allowed', false, 'reason', 'user_profile_not_ready');
  end if;

  if p_rate_limit < 1 or p_rate_limit > 60 then
    return jsonb_build_object('allowed', false, 'reason', 'invalid_rate_limit');
  end if;

  if (
    select count(*)
    from public.generations
    where user_id = p_user_id
      and created_at > reserved_at - interval '1 minute'
  ) >= p_rate_limit then
    return jsonb_build_object('allowed', false, 'reason', 'rate_limited');
  end if;

  if not exists (
    select 1
    from public.styles
    where id = p_style_id and is_active
  ) then
    return jsonb_build_object('allowed', false, 'reason', 'style_not_found');
  end if;

  if not exists (
    select 1
    from public.photo_processing_consents
    where id = p_photo_consent_id
      and user_id = p_user_id
      and consent_given
      and consent_version = 'photo-beta-2026-07-10'
      and consent_scope = 'smile_visualization'
      and photo_object_path = p_original_photo_path
  ) then
    return jsonb_build_object('allowed', false, 'reason', 'invalid_photo_consent');
  end if;

  select * into selected_pack
  from public.packs
  where user_id = p_user_id
    and generations_used < generations_total
    and (expires_at is null or expires_at > reserved_at)
  order by purchased_at asc, id asc
  limit 1
  for update;

  if selected_pack.id is not null then
    update public.packs
    set generations_used = generations_used + 1
    where id = selected_pack.id;

    insert into public.generations (
      user_id,
      style_id,
      photo_consent_id,
      original_photo_url,
      status,
      has_watermark,
      quota_source,
      quota_pack_id,
      quota_state,
      quota_reserved_at
    ) values (
      p_user_id,
      p_style_id,
      p_photo_consent_id,
      p_original_photo_path,
      'pending',
      false,
      'pack',
      selected_pack.id,
      'reserved',
      reserved_at
    ) returning * into created_generation;
  elsif reserved_user.free_gens_used < 1 then
    update public.users
    set free_gens_used = free_gens_used + 1
    where id = p_user_id;

    insert into public.generations (
      user_id,
      style_id,
      photo_consent_id,
      original_photo_url,
      status,
      has_watermark,
      quota_source,
      quota_state,
      quota_reserved_at
    ) values (
      p_user_id,
      p_style_id,
      p_photo_consent_id,
      p_original_photo_path,
      'pending',
      true,
      'free',
      'reserved',
      reserved_at
    ) returning * into created_generation;
  else
    return jsonb_build_object('allowed', false, 'reason', 'limit_reached');
  end if;

  return jsonb_build_object(
    'allowed', true,
    'generation', to_jsonb(created_generation)
  );
end;
$$;

revoke all on function public.reserve_generation_quota(uuid, uuid, uuid, text, integer)
  from public, anon, authenticated;
grant execute on function public.reserve_generation_quota(uuid, uuid, uuid, text, integer)
  to service_role;

create or replace function public.settle_generation_quota()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  if old.quota_state is distinct from 'reserved' then
    return new;
  end if;

  -- Quota ownership is immutable after reservation. Only status/deletion settles it.
  new.quota_source := old.quota_source;
  new.quota_pack_id := old.quota_pack_id;
  new.quota_state := old.quota_state;
  new.quota_reserved_at := old.quota_reserved_at;
  new.quota_settled_at := old.quota_settled_at;
  new.quota_released_at := old.quota_released_at;

  if new.status = 'completed' then
    new.quota_state := 'consumed';
    new.quota_settled_at := now();
  elsif new.status = 'failed' or new.deleted_at is not null then
    if old.quota_source = 'pack' then
      update public.packs
      set generations_used = greatest(generations_used - 1, 0)
      where id = old.quota_pack_id;
    elsif old.quota_source = 'free' then
      update public.users
      set free_gens_used = greatest(free_gens_used - 1, 0)
      where id = old.user_id;
    end if;
    new.quota_state := 'released';
    new.quota_released_at := now();
  end if;

  return new;
end;
$$;

revoke all on function public.settle_generation_quota() from public;

create trigger generations_settle_quota_before_update
  before update of status, deleted_at, quota_source, quota_pack_id, quota_state,
    quota_reserved_at, quota_settled_at, quota_released_at
  on generations
  for each row execute function public.settle_generation_quota();
