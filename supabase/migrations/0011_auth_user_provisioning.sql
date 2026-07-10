-- Keep the application user profile in sync with Supabase Auth. Without this
-- trigger, a real OTP signup has no public.users row and generation/quota writes
-- fail their foreign-key checks.

create or replace function public.sync_auth_user_profile()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.users (id, phone, email)
  values (new.id, new.phone, new.email)
  on conflict (id) do update
    set phone = excluded.phone,
        email = excluded.email;
  return new;
end;
$$;

revoke all on function public.sync_auth_user_profile() from public;

drop trigger if exists sync_auth_user_profile_after_write on auth.users;
create trigger sync_auth_user_profile_after_write
  after insert or update of phone, email on auth.users
  for each row execute function public.sync_auth_user_profile();

-- Backfill OTP users created before this migration is applied.
insert into public.users (id, phone, email)
select id, phone, email
from auth.users
on conflict (id) do update
  set phone = excluded.phone,
      email = excluded.email;
