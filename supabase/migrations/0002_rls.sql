-- Row Level Security policies (architecture §10.2).
-- Users may only read/write their own data. The API gateway uses the service-role
-- key (bypasses RLS) for admin / clinic / pipeline operations; these policies
-- protect direct client access via the anon key + user JWT.

alter table users       enable row level security;
alter table generations enable row level security;
alter table packs       enable row level security;
alter table payments    enable row level security;
alter table leads       enable row level security;
alter table styles      enable row level security;
alter table clinics     enable row level security;

-- users: a row is owned by the matching auth uid
create policy users_self_select on users
  for select using (auth.uid() = id);
create policy users_self_update on users
  for update using (auth.uid() = id);

-- generations: owner-only
create policy generations_owner_select on generations
  for select using (auth.uid() = user_id);
create policy generations_owner_insert on generations
  for insert with check (auth.uid() = user_id);
create policy generations_owner_delete on generations
  for delete using (auth.uid() = user_id);

-- packs: owner read-only from client (writes happen server-side after payment)
create policy packs_owner_select on packs
  for select using (auth.uid() = user_id);

-- payments: owner read-only
create policy payments_owner_select on payments
  for select using (auth.uid() = user_id);

-- leads: owner read-only (clinic-side access is via service role on the gateway)
create policy leads_owner_select on leads
  for select using (auth.uid() = user_id);

-- styles: publicly readable (only active ones surfaced by the API)
create policy styles_public_select on styles
  for select using (is_active = true);

-- clinics: publicly readable when active/trial
create policy clinics_public_select on clinics
  for select using (status in ('active', 'trial'));
