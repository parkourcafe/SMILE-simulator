-- Lead price currency per clinic. Russia = RUB, Uzbekistan = UZS (Partner Brief §19.2:
-- Tashkent lead pricing is in UZS sum, lower than Russia). The numeric amount stays in
-- lead_price_rub; this column records which currency that amount is in.

alter table clinics
  add column if not exists lead_price_currency text not null default 'RUB';
