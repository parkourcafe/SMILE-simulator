-- Private storage bucket for original + result photos (architecture §10.3:
-- private bucket, signed URLs only, no public URLs / no CDN caching of photos).

insert into storage.buckets (id, name, public)
values ('photos', 'photos', false)
on conflict (id) do nothing;

-- Authenticated users may read/write only objects under their own uid prefix:
--   photos/<auth.uid()>/...
-- The API gateway uses the service-role key and bypasses these policies when it
-- writes result/mask images on the user's behalf.
create policy "photos_owner_rw" on storage.objects
  for all to authenticated
  using (bucket_id = 'photos' and (storage.foldername(name))[1] = auth.uid()::text)
  with check (bucket_id = 'photos' and (storage.foldername(name))[1] = auth.uid()::text);
