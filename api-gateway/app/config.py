"""Application configuration, loaded from environment / .env (see .env.example)."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_env: str = "development"
    api_base_url: str = "http://localhost:8000"

    # Supabase
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""
    supabase_storage_bucket: str = "photos"

    # Inference
    inference_provider: str = "fal_flux_pro_fill"
    fal_api_key: str = ""
    fal_flux_fill_endpoint: str = "fal-ai/flux-pro/v1/fill"

    # Limits
    free_generations: int = 1
    rate_limit_per_minute: int = 5

    # Payments
    yookassa_shop_id: str = ""
    yookassa_secret_key: str = ""
    click_secret_key: str = ""

    # Admin / clinic auth
    admin_api_key: str = "change-me"

    # Clinic notifications (Phase 5). Email is the MVP channel; WhatsApp is preferred
    # when configured. All optional — unset means that channel is skipped.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "AI Smile Simulator <noreply@smilesim.app>"
    smtp_use_tls: bool = True
    whatsapp_api_base: str = "https://graph.facebook.com/v21.0"
    whatsapp_token: str = ""
    whatsapp_phone_id: str = ""

    # Misc
    photo_retention_days: int = 30
    result_image_size: int = 1024

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in {"production", "prod"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
