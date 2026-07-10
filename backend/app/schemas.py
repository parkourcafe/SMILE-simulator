"""Pydantic request/response models for the API (architecture §4)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

GenerationStatus = str  # pending | processing | completed | failed
PackTypeStr = str  # mini | main | extended | promo


# --- Auth / user ------------------------------------------------------------
class UserProfile(BaseModel):
    id: UUID
    phone: str | None = None
    email: str | None = None
    display_name: str | None = None
    city: str | None = None
    free_gens_used: int = 0


# --- Generation -------------------------------------------------------------
class GenerateRequest(BaseModel):
    """Client uploads the photo directly to Storage, then calls generate with its path."""

    style_id: UUID
    original_photo_path: str = Field(
        ..., description="Path of the uploaded selfie inside the private storage bucket"
    )


class GenerationOut(BaseModel):
    id: UUID
    status: GenerationStatus
    style_id: UUID | None = None
    original_photo_url: str | None = None
    result_photo_url: str | None = None
    has_watermark: bool = False
    quality_score: float | None = None
    inference_duration_ms: int | None = None
    error_message: str | None = None
    created_at: datetime | None = None


class GenerationListOut(BaseModel):
    items: list[GenerationOut]
    next_cursor: str | None = None


class RetryRequest(BaseModel):
    style_id: UUID | None = None  # optionally retry with a different style


# --- Styles -----------------------------------------------------------------
class StyleOut(BaseModel):
    id: UUID
    name: str
    name_ru: str
    thumbnail_url: str | None = None
    is_premium: bool = False
    sort_order: int = 0


# --- Price estimates (v1.1 cost anchor) -------------------------------------
class PriceEstimateOut(BaseModel):
    id: UUID
    city: str
    style_id: UUID | None = None
    treatment_label: str
    treatment_label_ru: str
    price_min: float
    price_max: float
    currency: str
    is_estimate: bool = True


# --- Packs / payments -------------------------------------------------------
class PackOption(BaseModel):
    pack_type: PackTypeStr
    generations_total: int
    price_amount: float
    price_currency: str
    title: str


class PurchaseRequest(BaseModel):
    pack_type: PackTypeStr
    provider: str  # yookassa | click | payme | apple_iap | google_play


class PurchaseResponse(BaseModel):
    payment_id: UUID
    payment_url: str | None = None  # redirect URL for web checkout providers


class MyPackOut(BaseModel):
    id: UUID
    pack_type: PackTypeStr
    generations_total: int
    generations_used: int
    expires_at: datetime | None = None


# --- Clinics / leads --------------------------------------------------------
class ClinicOut(BaseModel):
    id: UUID
    name: str
    city: str
    address: str | None = None
    lat: float | None = None
    lng: float | None = None
    logo_url: str | None = None
    specialties: list[str] = []
    distance_km: float | None = None


class LeadRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    clinic_id: UUID
    generation_id: UUID
    name: str = Field(min_length=1, max_length=120)
    phone: str = Field(pattern=r"^\+[1-9]\d{7,14}$")
    preferred_time: Literal["morning", "afternoon", "evening"] | None = None
    consent_given: Literal[True]
    consent_version: str = Field(min_length=1, max_length=80)
    consent_locale: Literal["ru", "en", "uz"]


class LeadOut(BaseModel):
    id: UUID
    clinic_id: UUID
    status: str
    created_at: datetime | None = None
