-- DEV / TEST seed data — partner clinics in Moscow & Saint Petersburg.
-- NOT a numbered migration on purpose: this is fake data for exercising the
-- "Find a clinic" -> lead -> notification flow. Do NOT run against production.
--
-- Emails use Gmail plus-addressing (parkourcafe+<slug>@gmail.com) so lead
-- notifications during testing land in one real inbox.
-- Run with: supabase db execute --file supabase/seed_dev.sql  (or psql).

insert into clinics (name, city, address, lat, lng, phone, email, website, specialties, lead_price_rub, lead_price_currency, status)
values
  -- Russia (RUB lead pricing 500–1500₽)
  ('Белая Линия', 'Moscow', 'ул. Тверская, 12, Москва',
   55.762200, 37.606500, '+74951111111', 'parkourcafe+belaya@gmail.com',
   'https://example.com/belaya', '{veneers,whitening}', 900, 'RUB', 'trial'),
  ('Dental Art Moscow', 'Moscow', 'Кутузовский пр-т, 30, Москва',
   55.740400, 37.534700, '+74952222222', 'parkourcafe+dentalart@gmail.com',
   'https://example.com/dentalart', '{veneers,implants,orthodontics}', 1200, 'RUB', 'trial'),
  ('SmileLab', 'Moscow', 'ул. Арбат, 25, Москва',
   55.749700, 37.591900, '+74953333333', 'parkourcafe+smilelab@gmail.com',
   'https://example.com/smilelab', '{whitening,orthodontics}', 700, 'RUB', 'active'),
  ('Невский Дент', 'SPb', 'Невский пр-т, 80, Санкт-Петербург',
   59.933500, 30.349500, '+78124444444', 'parkourcafe+nevsky@gmail.com',
   'https://example.com/nevsky', '{veneers,whitening}', 800, 'RUB', 'trial'),
  ('Балтийская Улыбка', 'SPb', 'Большой пр-т П.С., 50, Санкт-Петербург',
   59.961200, 30.295800, '+78125555555', 'parkourcafe+baltic@gmail.com',
   'https://example.com/baltic', '{implants,veneers}', 1100, 'RUB', 'trial'),
  ('SPb Aesthetic Dental', 'SPb', 'Московский пр-т, 150, Санкт-Петербург',
   59.886900, 30.318700, '+78126666666', 'parkourcafe+aesthetic@gmail.com',
   'https://example.com/aesthetic', '{whitening,orthodontics}', 650, 'RUB', 'active'),
  -- Uzbekistan (UZS lead pricing 30,000–50,000 sum — Partner Brief §19.2)
  ('Dental City Tashkent', 'Tashkent', 'Amir Temur ko''chasi, 15, Toshkent',
   41.311100, 69.279700, '+998711111111', 'parkourcafe+dentalcity@gmail.com',
   'https://example.com/dentalcity', '{veneers,whitening}', 40000, 'UZS', 'trial'),
  ('Smile Tashkent', 'Tashkent', 'Mustaqillik ko''chasi, 40, Toshkent',
   41.299500, 69.268500, '+998712222222', 'parkourcafe+smiletashkent@gmail.com',
   'https://example.com/smiletashkent', '{whitening,orthodontics}', 35000, 'UZS', 'trial'),
  ('Oqtepa Dental', 'Tashkent', 'Bunyodkor shoh ko''chasi, 7, Toshkent',
   41.285300, 69.203400, '+998713333333', 'parkourcafe+oqtepa@gmail.com',
   'https://example.com/oqtepa', '{veneers,implants}', 45000, 'UZS', 'active'),
  ('Tashkent Aesthetic Dental', 'Tashkent', 'Shota Rustaveli ko''chasi, 22, Toshkent',
   41.296800, 69.252100, '+998714444444', 'parkourcafe+tashaesthetic@gmail.com',
   'https://example.com/tashaesthetic', '{veneers,whitening}', 50000, 'UZS', 'trial');
