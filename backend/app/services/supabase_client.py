"""Thin async Supabase client (PostgREST + Storage) built on httpx.

We deliberately avoid the heavy ``supabase-py`` SDK: the gateway only needs a
handful of REST calls, and a thin wrapper keeps cold starts fast on Railway.

The gateway uses the **service-role** key, which bypasses RLS. RLS still protects
direct client access via the anon key (see migration 0002_rls.sql). All ownership
checks for service-role calls must therefore be enforced in application code.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.config import Settings, get_settings


class SupabaseError(RuntimeError):
    pass


class SupabaseClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    @property
    def configured(self) -> bool:
        return bool(self.settings.supabase_url and self.settings.supabase_service_role_key)

    def _require(self) -> None:
        if not self.configured:
            raise SupabaseError(
                "Supabase is not configured. Set SUPABASE_URL and "
                "SUPABASE_SERVICE_ROLE_KEY (see .env.example)."
            )

    @property
    def _rest_base(self) -> str:
        return f"{self.settings.supabase_url}/rest/v1"

    @property
    def _storage_base(self) -> str:
        return f"{self.settings.supabase_url}/storage/v1"

    def _headers(self, *, prefer: str | None = None) -> dict[str, str]:
        key = self.settings.supabase_service_role_key
        headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }
        if prefer:
            headers["Prefer"] = prefer
        # Target a non-default Postgres schema via PostgREST profile headers. Only sent
        # when the app tables live outside `public` (the schema must be exposed to
        # PostgREST). Accept-Profile applies to reads, Content-Profile to writes.
        schema = self.settings.supabase_db_schema
        if schema and schema != "public":
            headers["Accept-Profile"] = schema
            headers["Content-Profile"] = schema
        return headers

    # --- PostgREST helpers --------------------------------------------------
    async def select(
        self, table: str, *, filters: dict[str, str] | None = None, limit: int | None = None
    ) -> list[dict[str, Any]]:
        self._require()
        params: dict[str, str] = {"select": "*", **(filters or {})}
        if limit is not None:
            params["limit"] = str(limit)
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{self._rest_base}/{table}", headers=self._headers(), params=params
            )
        if resp.status_code >= 400:
            raise SupabaseError(f"select {table} failed: {resp.status_code} {resp.text}")
        return resp.json()

    async def insert(self, table: str, row: dict[str, Any]) -> dict[str, Any]:
        self._require()
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{self._rest_base}/{table}",
                headers=self._headers(prefer="return=representation"),
                json=row,
            )
        if resp.status_code >= 400:
            raise SupabaseError(f"insert {table} failed: {resp.status_code} {resp.text}")
        data = resp.json()
        return data[0] if isinstance(data, list) else data

    async def update(
        self, table: str, *, filters: dict[str, str], patch: dict[str, Any]
    ) -> list[dict[str, Any]]:
        self._require()
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.patch(
                f"{self._rest_base}/{table}",
                headers=self._headers(prefer="return=representation"),
                params=filters,
                json=patch,
            )
        if resp.status_code >= 400:
            raise SupabaseError(f"update {table} failed: {resp.status_code} {resp.text}")
        return resp.json()

    # --- Storage helpers ----------------------------------------------------
    async def create_signed_url(self, path: str, *, expires_in: int = 3600) -> str:
        """Generate a short-lived signed URL for a private object."""
        self._require()
        bucket = self.settings.supabase_storage_bucket
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{self._storage_base}/object/sign/{bucket}/{path}",
                headers=self._headers(),
                json={"expiresIn": expires_in},
            )
        if resp.status_code >= 400:
            raise SupabaseError(f"sign url failed: {resp.status_code} {resp.text}")
        signed = resp.json()["signedURL"]
        return f"{self.settings.supabase_url}/storage/v1{signed}"

    async def upload(self, path: str, data: bytes, *, content_type: str = "image/png") -> str:
        """Upload bytes to the private bucket; returns the object path."""
        self._require()
        bucket = self.settings.supabase_storage_bucket
        headers = {
            "apikey": self.settings.supabase_service_role_key,
            "Authorization": f"Bearer {self.settings.supabase_service_role_key}",
            "Content-Type": content_type,
            "x-upsert": "true",
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self._storage_base}/object/{bucket}/{path}", headers=headers, content=data
            )
        if resp.status_code >= 400:
            raise SupabaseError(f"upload failed: {resp.status_code} {resp.text}")
        return path

    async def download(self, path: str) -> bytes:
        self._require()
        bucket = self.settings.supabase_storage_bucket
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self._storage_base}/object/{bucket}/{path}", headers=self._headers()
            )
        if resp.status_code >= 400:
            raise SupabaseError(f"download failed: {resp.status_code} {resp.text}")
        return resp.content


_client: SupabaseClient | None = None


def get_supabase() -> SupabaseClient:
    global _client
    if _client is None:
        _client = SupabaseClient()
    return _client
