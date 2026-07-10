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
        return self.settings.supabase_configured

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
        key = self.settings.supabase_server_key
        headers = {
            "apikey": key,
            "Content-Type": "application/json",
        }
        # Current sb_secret keys are opaque API keys and must not be sent as JWTs.
        # The legacy service_role key is a JWT and still needs the bearer header.
        if not key.startswith("sb_secret_"):
            headers["Authorization"] = f"Bearer {key}"
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
            raise SupabaseError(f"select {table} failed with status {resp.status_code}")
        return resp.json()

    async def ping(self) -> None:
        """Verify PostgREST and the minimum production schema used by the API."""
        self._require()
        required_schema = (
            ("styles", "id"),
            ("generations", "id,photo_consent_id,quota_state"),
            ("photo_processing_consents", "id,photo_object_path"),
            ("leads", "id,idempotency_key,transfer_consent_given"),
            ("clinic_api_keys", "id,key_hash,status"),
            (
                "payments",
                "id,pack_type,idempotency_key,provider_status,confirmation_url",
            ),
        )
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                for table, columns in required_schema:
                    resp = await client.get(
                        f"{self._rest_base}/{table}",
                        headers=self._headers(),
                        params={"select": columns, "limit": "1"},
                    )
                    if resp.status_code >= 400:
                        raise SupabaseError(
                            f"readiness schema check failed for {table}: {resp.status_code}"
                        )
                zero_uuid = "00000000-0000-0000-0000-000000000000"
                rpc_response = await client.post(
                    f"{self._rest_base}/rpc/reserve_generation_quota",
                    headers=self._headers(),
                    json={
                        "p_user_id": zero_uuid,
                        "p_style_id": zero_uuid,
                        "p_photo_consent_id": zero_uuid,
                        "p_original_photo_path": f"{zero_uuid}/readiness_probe",
                        "p_rate_limit": 1,
                    },
                )
                if rpc_response.status_code >= 400:
                    raise SupabaseError(
                        "readiness schema check failed for reserve_generation_quota: "
                        f"{rpc_response.status_code}"
                    )
                payment_rpc_response = await client.post(
                    f"{self._rest_base}/rpc/activate_yookassa_payment",
                    headers=self._headers(),
                    json={
                        "p_payment_id": zero_uuid,
                        "p_provider_payment_id": "readiness_probe",
                    },
                )
                if payment_rpc_response.status_code >= 400:
                    raise SupabaseError(
                        "readiness schema check failed for activate_yookassa_payment: "
                        f"{payment_rpc_response.status_code}"
                    )
        except httpx.HTTPError as exc:
            raise SupabaseError("readiness check could not reach Supabase") from exc

    async def insert(self, table: str, row: dict[str, Any]) -> dict[str, Any]:
        self._require()
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{self._rest_base}/{table}",
                headers=self._headers(prefer="return=representation"),
                json=row,
            )
        if resp.status_code >= 400:
            raise SupabaseError(f"insert {table} failed with status {resp.status_code}")
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
            raise SupabaseError(f"update {table} failed with status {resp.status_code}")
        return resp.json()

    async def rpc(self, function: str, params: dict[str, Any]) -> Any:
        """Call a service-only Postgres function through PostgREST."""
        self._require()
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{self._rest_base}/rpc/{function}",
                headers=self._headers(),
                json=params,
            )
        if resp.status_code >= 400:
            raise SupabaseError(f"rpc {function} failed with status {resp.status_code}")
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
            raise SupabaseError(f"sign url failed with status {resp.status_code}")
        signed = resp.json()["signedURL"]
        return f"{self.settings.supabase_url}/storage/v1{signed}"

    async def upload(self, path: str, data: bytes, *, content_type: str = "image/png") -> str:
        """Upload bytes to the private bucket; returns the object path."""
        self._require()
        bucket = self.settings.supabase_storage_bucket
        headers = self._headers()
        headers.update({"Content-Type": content_type, "x-upsert": "true"})
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self._storage_base}/object/{bucket}/{path}", headers=headers, content=data
            )
        if resp.status_code >= 400:
            raise SupabaseError(f"upload failed with status {resp.status_code}")
        return path

    async def download(self, path: str) -> bytes:
        self._require()
        bucket = self.settings.supabase_storage_bucket
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self._storage_base}/object/{bucket}/{path}", headers=self._headers()
            )
        if resp.status_code >= 400:
            raise SupabaseError(f"download failed with status {resp.status_code}")
        return resp.content

    async def remove_objects(self, paths: list[str]) -> list[dict[str, Any]]:
        """Delete objects through Storage API so both metadata and file bytes are removed."""
        self._require()
        unique_paths = list(dict.fromkeys(path for path in paths if path))
        if not unique_paths:
            return []

        bucket = self.settings.supabase_storage_bucket
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.request(
                "DELETE",
                f"{self._storage_base}/object/{bucket}",
                headers=self._headers(),
                json={"prefixes": unique_paths},
            )
        if resp.status_code >= 400:
            raise SupabaseError(f"storage delete failed with status {resp.status_code}")
        data = resp.json()
        return data if isinstance(data, list) else []


_client: SupabaseClient | None = None


def get_supabase() -> SupabaseClient:
    global _client
    if _client is None:
        _client = SupabaseClient()
    return _client
