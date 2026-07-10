"""Application configuration, loaded from environment / .env (see .env.example)."""

from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_env: str = "development"
    api_base_url: str = "http://localhost:8000"
    cors_allowed_origins: str = (
        "http://localhost:3000,http://localhost:8080,https://zubilook.com,https://www.zubilook.com"
    )

    # Mock flags (v1.1). Default TRUE so a fresh clone runs the whole product with
    # zero external credentials. Flip to false once real keys are in .env (see SETUP.md).
    mock_inference: bool = True  # MockProvider instead of Fal.ai
    mock_auth: bool = True  # accept a dev stub token instead of verifying Supabase JWT
    mock_payments: bool = True  # simulate YooKassa payment creation (webhook stays real)

    # Supabase
    supabase_url: str = ""
    supabase_publishable_key: str = ""
    supabase_secret_key: str = ""
    # Legacy key names remain supported during migration to Supabase's current
    # publishable/secret key system.
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""
    supabase_storage_bucket: str = "photos"
    # Postgres schema holding the app tables. "public" by default; set to a namespace
    # (e.g. "smile") when sharing a project — it must be exposed to PostgREST.
    supabase_db_schema: str = "public"

    # Inference
    inference_provider: str = "fal_flux_pro_fill"
    fal_api_key: str = ""
    fal_flux_fill_endpoint: str = "fal-ai/flux-pro/v1/fill"
    mediapipe_face_model: str = ""
    mediapipe_face_model_sha256: str = (
        "64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff"
    )

    # Limits
    rate_limit_per_minute: int = 5
    generation_reservation_timeout_minutes: int = 15
    max_request_body_bytes: int = 256 * 1024

    # Payments
    yookassa_shop_id: str = ""
    yookassa_secret_key: str = ""
    yookassa_return_url: str = ""
    click_secret_key: str = ""

    # Admin / clinic auth
    admin_api_key: str = "change-me"

    # Clinic notifications (Phase 5). Email is the MVP channel; WhatsApp is preferred
    # when configured. All optional — unset means that channel is skipped.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "ZubiLook <noreply@zubilook.com>"
    smtp_use_tls: bool = True
    whatsapp_api_base: str = "https://graph.facebook.com/v21.0"
    whatsapp_token: str = ""
    whatsapp_phone_id: str = ""

    # Error tracking. Optional outside production; required by the production guard.
    sentry_dsn: str = ""

    # Dev artifacts (branded-result HTML rendered to file when SMTP is unconfigured).
    artifacts_dir: str = ".artifacts"

    # Misc
    photo_retention_days: int = 30
    result_image_size: int = 1024

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in {"production", "prod"}

    @property
    def cors_origins(self) -> list[str]:
        return list(
            dict.fromkeys(
                origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()
            )
        )

    @property
    def supabase_public_key(self) -> str:
        return self.supabase_publishable_key or self.supabase_anon_key

    @property
    def supabase_server_key(self) -> str:
        return self.supabase_secret_key or self.supabase_service_role_key

    @property
    def supabase_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_server_key)

    @property
    def supabase_auth_issuer(self) -> str:
        return f"{self.supabase_url.rstrip('/')}/auth/v1"

    @property
    def face_model_path(self) -> Path:
        if self.mediapipe_face_model:
            return Path(self.mediapipe_face_model)
        return Path(__file__).resolve().parents[1] / ".cache" / "face_landmarker.task"

    def face_model_is_valid(self) -> bool:
        path = self.face_model_path
        try:
            if not path.is_file():
                return False
            if not self.mediapipe_face_model_sha256:
                return True
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            return digest == self.mediapipe_face_model_sha256.lower()
        except OSError:
            return False

    def assert_safe_startup(self) -> None:
        """Refuse a production process that would expose mock or default credentials."""
        if not self.is_production:
            return

        errors: list[str] = []
        if self.mock_auth:
            errors.append("MOCK_AUTH must be false")
        if self.mock_inference:
            errors.append("MOCK_INFERENCE must be false")
        if self.mock_payments:
            errors.append("MOCK_PAYMENTS must be false")
        if not self.supabase_url:
            errors.append("SUPABASE_URL is required")
        if not self.supabase_public_key:
            errors.append("SUPABASE_PUBLISHABLE_KEY is required")
        if not self.supabase_server_key:
            errors.append("SUPABASE_SECRET_KEY is required")
        if (
            not self.admin_api_key
            or self.admin_api_key == "change-me"
            or len(self.admin_api_key) < 32
        ):
            errors.append("ADMIN_API_KEY must be a non-default value of at least 32 characters")
        if "*" in self.cors_origins:
            errors.append("CORS_ALLOWED_ORIGINS cannot contain '*' in production")
        if any("localhost" in origin or "127.0.0.1" in origin for origin in self.cors_origins):
            errors.append("CORS_ALLOWED_ORIGINS cannot contain local origins in production")
        if not self.fal_api_key:
            errors.append("FAL_API_KEY is required")
        if not self.face_model_is_valid():
            errors.append("MEDIAPIPE_FACE_MODEL must exist and match its SHA-256 checksum")
        if not (self.yookassa_shop_id and self.yookassa_secret_key):
            errors.append("YooKassa credentials are required")
        if (
            not self.yookassa_return_url.startswith("https://")
            or "localhost" in self.yookassa_return_url
            or "127.0.0.1" in self.yookassa_return_url
        ):
            errors.append("YOOKASSA_RETURN_URL must be a public HTTPS URL")
        if not self.smtp_host and not (self.whatsapp_token and self.whatsapp_phone_id):
            errors.append("SMTP or WhatsApp clinic notifications must be configured")
        if not self.sentry_dsn.startswith("https://"):
            errors.append("SENTRY_DSN must be a configured HTTPS DSN")
        if not 1 <= self.photo_retention_days <= 30:
            errors.append("PHOTO_RETENTION_DAYS must be between 1 and 30")
        if not 5 <= self.generation_reservation_timeout_minutes <= 60:
            errors.append("GENERATION_RESERVATION_TIMEOUT_MINUTES must be between 5 and 60")
        if not 1 <= self.rate_limit_per_minute <= 60:
            errors.append("RATE_LIMIT_PER_MINUTE must be between 1 and 60")
        if not 16 * 1024 <= self.max_request_body_bytes <= 1024 * 1024:
            errors.append("MAX_REQUEST_BODY_BYTES must be between 16384 and 1048576")

        if errors:
            raise RuntimeError("Unsafe production configuration: " + "; ".join(errors))


@lru_cache
def get_settings() -> Settings:
    return Settings()
