#!/usr/bin/env bash
set -euo pipefail

user_id="00000000-0000-0000-0000-000000000104"
consent_id="10000000-0000-0000-0000-000000000104"
photo_path="${user_id}/${consent_id}_original"

psql --set ON_ERROR_STOP=1 <<SQL
insert into auth.users (id, phone) values ('${user_id}', '+70000000104');
insert into public.photo_processing_consents (
  id, user_id, consent_given, consent_version, consent_locale, consent_scope,
  photo_object_path, consented_at
) values (
  '${consent_id}', '${user_id}', true, 'photo-beta-2026-07-10', 'ru',
  'smile_visualization', '${photo_path}', now()
);
SQL

query="select public.reserve_generation_quota(
  '${user_id}',
  (select id from public.styles where name = 'Natural White'),
  '${consent_id}',
  '${photo_path}',
  5
);"

result_dir="$(mktemp -d)"
trap 'rm -rf "$result_dir"' EXIT

psql --no-psqlrc --quiet --tuples-only --no-align --set ON_ERROR_STOP=1 \
  --command "$query" >"$result_dir/first" &
first_pid=$!
psql --no-psqlrc --quiet --tuples-only --no-align --set ON_ERROR_STOP=1 \
  --command "$query" >"$result_dir/second" &
second_pid=$!

wait "$first_pid"
wait "$second_pid"

allowed_count="$(grep --no-filename --count '"allowed": true' "$result_dir/first" "$result_dir/second" | awk '{sum += $1} END {print sum + 0}')"
denied_count="$(grep --no-filename --count '"reason": "limit_reached"' "$result_dir/first" "$result_dir/second" | awk '{sum += $1} END {print sum + 0}')"

if [[ "$allowed_count" != "1" || "$denied_count" != "1" ]]; then
  echo "Expected one allowed and one denied reservation" >&2
  cat "$result_dir/first" "$result_dir/second" >&2
  exit 1
fi

psql --set ON_ERROR_STOP=1 --tuples-only --no-align <<SQL | grep --quiet '^1|1$'
select
  (select count(*) from public.generations where user_id = '${user_id}') as generations,
  (select free_gens_used from public.users where id = '${user_id}') as free_used;
SQL
