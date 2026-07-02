-- RLS for price_estimates (v1.1): publicly readable when active, like styles/clinics.
-- Writes happen server-side via the service-role key.

alter table price_estimates enable row level security;

create policy price_estimates_public_select on price_estimates
  for select using (is_active = true);
