-- Photo deletion lifecycle. Storage objects are removed through the Storage API;
-- these columns make deletion retryable and keep only a non-image tombstone when a
-- generation is linked to a clinic lead.

alter table generations alter column original_photo_url drop not null;

alter table generations
  add column deleted_at timestamptz,
  add column photo_deletion_pending boolean not null default false,
  add column photo_deleted_at timestamptz,
  add column photo_deletion_reason text
    check (photo_deletion_reason is null or photo_deletion_reason in (
      'deleted_by_user',
      'retention_expired',
      'account_deleted'
    ));

create index generations_photo_retention_idx
  on generations (created_at)
  where deleted_at is null or photo_deletion_pending;

-- A direct row delete would orphan the underlying Storage objects. Deletion must go
-- through the API gateway, which deletes Storage first and leaves a retryable tombstone.
drop policy if exists generations_owner_delete on generations;
