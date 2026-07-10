-- Durable, idempotent YooKassa payment intents and atomic pack activation.

alter table payments alter column provider_payment_id drop not null;

alter table payments
  add column pack_type pack_type,
  add column idempotency_key uuid,
  add column provider_status text
    check (provider_status is null or provider_status in (
      'pending', 'waiting_for_capture', 'succeeded', 'canceled'
    )),
  add column confirmation_url text
    check (confirmation_url is null or confirmation_url ~ '^https://'),
  add constraint payments_intent_metadata_complete check (
    (pack_type is null and idempotency_key is null) or
    (pack_type is not null and idempotency_key is not null)
  );

create unique index payments_user_idempotency_uniq
  on payments (user_id, idempotency_key)
  where idempotency_key is not null;

alter table packs
  add column payment_id uuid references payments(id) on delete set null;

create unique index packs_payment_id_uniq
  on packs (payment_id)
  where payment_id is not null;

create or replace function public.activate_yookassa_payment(
  p_payment_id uuid,
  p_provider_payment_id text
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  payment public.payments%rowtype;
  created_pack public.packs%rowtype;
  expected_generations integer;
  expected_amount numeric(10,2);
begin
  select * into payment
  from public.payments
  where id = p_payment_id
  for update;

  if payment.id is null then
    return jsonb_build_object('activated', false, 'reason', 'payment_not_found');
  end if;

  if payment.status = 'completed' then
    return jsonb_build_object(
      'activated', false,
      'duplicate', true,
      'pack_id', payment.pack_id
    );
  end if;

  if payment.status is distinct from 'pending' then
    return jsonb_build_object('activated', false, 'reason', 'payment_not_pending');
  end if;

  if payment.provider <> 'yookassa' or payment.currency <> 'RUB' then
    return jsonb_build_object('activated', false, 'reason', 'payment_provider_mismatch');
  end if;

  if payment.provider_status is distinct from 'succeeded' then
    return jsonb_build_object('activated', false, 'reason', 'payment_not_verified');
  end if;

  if p_provider_payment_id is null or length(trim(p_provider_payment_id)) = 0 or
     (payment.provider_payment_id is not null and
      payment.provider_payment_id <> p_provider_payment_id) then
    return jsonb_build_object('activated', false, 'reason', 'provider_payment_mismatch');
  end if;

  case payment.pack_type
    when 'mini' then
      expected_generations := 5;
      expected_amount := 149.00;
    when 'main' then
      expected_generations := 20;
      expected_amount := 499.00;
    when 'extended' then
      expected_generations := 50;
      expected_amount := 899.00;
    else
      return jsonb_build_object('activated', false, 'reason', 'unknown_pack');
  end case;

  if payment.amount <> expected_amount then
    return jsonb_build_object('activated', false, 'reason', 'payment_amount_mismatch');
  end if;

  insert into public.packs (
    user_id,
    pack_type,
    generations_total,
    generations_used,
    price_amount,
    price_currency,
    payment_id
  ) values (
    payment.user_id,
    payment.pack_type,
    expected_generations,
    0,
    payment.amount,
    payment.currency,
    payment.id
  ) returning * into created_pack;

  update public.payments
  set provider_payment_id = p_provider_payment_id,
      provider_status = 'succeeded',
      status = 'completed',
      pack_id = created_pack.id,
      completed_at = now()
  where id = payment.id;

  return jsonb_build_object(
    'activated', true,
    'duplicate', false,
    'pack_id', created_pack.id
  );
end;
$$;

revoke all on function public.activate_yookassa_payment(uuid, text)
  from public, anon, authenticated;
grant execute on function public.activate_yookassa_payment(uuid, text)
  to service_role;
