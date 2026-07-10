-- Behavioral assertions for auth provisioning, consent-bound uploads, and atomic quota.

do $$
declare
  free_user constant uuid := '00000000-0000-0000-0000-000000000101';
  failed_user constant uuid := '00000000-0000-0000-0000-000000000102';
  pack_user constant uuid := '00000000-0000-0000-0000-000000000103';
  payment_user constant uuid := '00000000-0000-0000-0000-000000000105';
  free_consent constant uuid := '10000000-0000-0000-0000-000000000101';
  failed_consent constant uuid := '10000000-0000-0000-0000-000000000102';
  pack_consent constant uuid := '10000000-0000-0000-0000-000000000103';
  expired_pack constant uuid := '20000000-0000-0000-0000-000000000101';
  active_pack constant uuid := '20000000-0000-0000-0000-000000000102';
  payment constant uuid := '30000000-0000-0000-0000-000000000105';
  payment_key constant uuid := '40000000-0000-0000-0000-000000000105';
  provider_payment constant text := '2fdd9000-000f-5000-a000-123456789abc';
  style uuid;
  result jsonb;
  generation uuid;
begin
  select id into style from public.styles where name = 'Natural White';
  if style is null then
    raise exception 'style seed missing';
  end if;

  insert into auth.users (id, phone) values
    (free_user, '+70000000101'),
    (failed_user, '+70000000102'),
    (pack_user, '+70000000103'),
    (payment_user, '+70000000105');

  if (select count(*) from public.users where id in (free_user, failed_user, pack_user, payment_user)) <> 4 then
    raise exception 'auth user provisioning trigger did not backfill profiles';
  end if;

  insert into public.photo_processing_consents (
    id, user_id, consent_given, consent_version, consent_locale, consent_scope,
    photo_object_path, consented_at
  ) values
    (
      free_consent, free_user, true, 'photo-beta-2026-07-10', 'ru',
      'smile_visualization', free_user::text || '/' || free_consent::text || '_original', now()
    ),
    (
      failed_consent, failed_user, true, 'photo-beta-2026-07-10', 'ru',
      'smile_visualization', failed_user::text || '/' || failed_consent::text || '_original', now()
    ),
    (
      pack_consent, pack_user, true, 'photo-beta-2026-07-10', 'ru',
      'smile_visualization', pack_user::text || '/' || pack_consent::text || '_original', now()
    );

  result := public.reserve_generation_quota(
    free_user,
    style,
    free_consent,
    free_user::text || '/' || free_consent::text || '_original',
    5
  );
  if result->>'allowed' <> 'true' then
    raise exception 'first free reservation was denied: %', result;
  end if;
  generation := (result->'generation'->>'id')::uuid;

  result := public.reserve_generation_quota(
    free_user,
    style,
    free_consent,
    free_user::text || '/' || free_consent::text || '_original',
    5
  );
  if result->>'reason' <> 'limit_reached' then
    raise exception 'second free reservation was not denied: %', result;
  end if;
  if (select free_gens_used from public.users where id = free_user) <> 1 then
    raise exception 'free reservation counter is not exactly one';
  end if;

  update public.generations set status = 'completed' where id = generation;
  if (select quota_state from public.generations where id = generation) <> 'consumed' then
    raise exception 'successful generation did not consume reservation';
  end if;

  result := public.reserve_generation_quota(
    failed_user,
    style,
    failed_consent,
    failed_user::text || '/' || failed_consent::text || '_original',
    5
  );
  generation := (result->'generation'->>'id')::uuid;
  update public.generations set status = 'failed' where id = generation;
  if (select quota_state from public.generations where id = generation) <> 'released' then
    raise exception 'failed generation did not release reservation';
  end if;
  if (select free_gens_used from public.users where id = failed_user) <> 0 then
    raise exception 'failed generation did not restore free counter';
  end if;

  update public.users set free_gens_used = 1 where id = pack_user;
  insert into public.packs (
    id, user_id, pack_type, generations_total, generations_used,
    price_amount, price_currency, purchased_at, expires_at
  ) values
    (expired_pack, pack_user, 'mini', 5, 0, 149, 'RUB', now() - interval '2 days', now() - interval '1 day'),
    (active_pack, pack_user, 'main', 20, 0, 499, 'RUB', now() - interval '1 day', now() + interval '30 days');

  result := public.reserve_generation_quota(
    pack_user,
    style,
    pack_consent,
    pack_user::text || '/' || pack_consent::text || '_original',
    5
  );
  if result->>'allowed' <> 'true' then
    raise exception 'active pack reservation was denied: %', result;
  end if;
  if (result->'generation'->>'quota_pack_id')::uuid <> active_pack then
    raise exception 'expired pack was selected instead of active pack';
  end if;
  if (select generations_used from public.packs where id = expired_pack) <> 0 or
     (select generations_used from public.packs where id = active_pack) <> 1 then
    raise exception 'pack counters were updated incorrectly';
  end if;

  result := public.reserve_generation_quota(
    pack_user,
    style,
    pack_consent,
    pack_user::text || '/' || pack_consent::text || '_original',
    1
  );
  if result->>'reason' <> 'rate_limited' then
    raise exception 'per-user generation rate limit was not enforced: %', result;
  end if;
  if (select generations_used from public.packs where id = active_pack) <> 1 then
    raise exception 'rate-limited request consumed a pack credit';
  end if;

  insert into public.payments (
    id, user_id, amount, currency, provider, provider_payment_id, status,
    pack_type, idempotency_key, provider_status
  ) values (
    payment, payment_user, 149.00, 'RUB', 'yookassa', provider_payment,
    'pending', 'mini', payment_key, null
  );

  result := public.activate_yookassa_payment(payment, provider_payment);
  if result->>'reason' <> 'payment_not_verified' then
    raise exception 'unverified payment was activated: %', result;
  end if;

  update public.payments
  set provider_status = 'succeeded', status = 'failed'
  where id = payment;
  result := public.activate_yookassa_payment(payment, provider_payment);
  if result->>'reason' <> 'payment_not_pending' then
    raise exception 'failed payment was activated: %', result;
  end if;

  update public.payments set status = 'pending' where id = payment;
  result := public.activate_yookassa_payment(payment, provider_payment);
  if result->>'activated' <> 'true' then
    raise exception 'verified payment did not activate a pack: %', result;
  end if;
  result := public.activate_yookassa_payment(payment, provider_payment);
  if result->>'duplicate' <> 'true' then
    raise exception 'duplicate payment activation was not idempotent: %', result;
  end if;
  if (select status from public.payments where id = payment) <> 'completed' or
     (select count(*) from public.packs where payment_id = payment) <> 1 then
    raise exception 'payment and pack linkage is inconsistent';
  end if;

  if (select count(*) from pg_policies where schemaname = 'storage' and policyname like 'photos_consented_%') <> 2 then
    raise exception 'consent-bound Storage policies are missing';
  end if;
end;
$$;
