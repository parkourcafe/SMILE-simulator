"""Idempotent B2B lead submission and clinic-side endpoints."""

from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException

from app.deps import CurrentUser, get_current_user
from app.schemas import LeadOut, LeadRequest
from app.services.branded_delivery import deliver_branded_result
from app.services.notifications import notify_clinic
from app.services.supabase_client import SupabaseError, get_supabase

router = APIRouter(tags=["leads"])
log = logging.getLogger("smile.leads")


def _lead_out(row: dict) -> LeadOut:
    return LeadOut(
        id=row["id"],
        clinic_id=row["clinic_id"],
        status=row["status"],
        created_at=row.get("created_at"),
    )


def _same_target(row: dict, body: LeadRequest) -> bool:
    return str(row["clinic_id"]) == str(body.clinic_id) and str(row["generation_id"]) == str(
        body.generation_id
    )


async def _existing_lead(sb, user_id: str, body: LeadRequest, idempotency_key: str) -> dict | None:
    rows = await sb.select(
        "leads",
        filters={"user_id": f"eq.{user_id}", "idempotency_key": f"eq.{idempotency_key}"},
        limit=1,
    )
    if rows:
        if not _same_target(rows[0], body):
            raise HTTPException(status_code=409, detail="idempotency_key_reused")
        return rows[0]

    rows = await sb.select(
        "leads",
        filters={"user_id": f"eq.{user_id}", "generation_id": f"eq.{body.generation_id}"},
        limit=1,
    )
    if rows:
        if str(rows[0]["clinic_id"]) != str(body.clinic_id):
            raise HTTPException(status_code=409, detail="generation_already_shared")
        return rows[0]
    return None


@router.post("/api/leads", response_model=LeadOut, status_code=201)
async def submit_lead(
    body: LeadRequest,
    idempotency_key: UUID = Header(alias="Idempotency-Key"),
    user: CurrentUser = Depends(get_current_user),
) -> LeadOut:
    sb = get_supabase()
    key = str(idempotency_key)

    existing = await _existing_lead(sb, user.id, body, key)
    if existing:
        return _lead_out(existing)

    clinics = await sb.select(
        "clinics",
        filters={"id": f"eq.{body.clinic_id}", "status": "in.(active,trial)"},
        limit=1,
    )
    if not clinics:
        raise HTTPException(status_code=404, detail="clinic_not_found")
    clinic = clinics[0]

    generations = await sb.select(
        "generations",
        filters={"id": f"eq.{body.generation_id}", "deleted_at": "is.null"},
        limit=1,
    )
    if not generations or generations[0]["user_id"] != user.id:
        raise HTTPException(status_code=404, detail="generation_not_found")
    generation = generations[0]
    if generation.get("status") != "completed" or not generation.get("result_photo_url"):
        raise HTTPException(status_code=409, detail="generation_not_ready")

    consented_at = datetime.now(UTC).isoformat()
    try:
        lead = await sb.insert(
            "leads",
            {
                "user_id": user.id,
                "clinic_id": str(body.clinic_id),
                "generation_id": str(body.generation_id),
                "user_name": body.name,
                "user_phone": body.phone,
                "preferred_time": body.preferred_time,
                "status": "new",
                "lead_cost_rub": clinic.get("lead_price_rub", 0),
                "idempotency_key": key,
                "transfer_consent_given": True,
                "transfer_consent_version": body.consent_version,
                "transfer_consent_locale": body.consent_locale,
                "transfer_consented_at": consented_at,
            },
        )
    except SupabaseError:
        # A concurrent retry may win either unique constraint. Return that row rather
        # than creating or notifying a second lead; re-raise unrelated DB errors.
        existing = await _existing_lead(sb, user.id, body, key)
        if not existing:
            raise
        return _lead_out(existing)

    result_url = None
    try:
        result_url = await sb.create_signed_url(generation["result_photo_url"], expires_in=3600)
    except SupabaseError:
        log.warning("result signing failed for lead %s", lead["id"])

    notice = await notify_clinic(clinic, lead, result_url)
    final_status = "notified" if notice.ok else "new"
    patch: dict = {"status": final_status}
    if notice.ok:
        patch["clinic_notified_at"] = datetime.now(UTC).isoformat()
    await sb.update("leads", filters={"id": f"eq.{lead['id']}"}, patch=patch)

    before_url = None
    if generation.get("original_photo_url"):
        try:
            before_url = await sb.create_signed_url(
                generation["original_photo_url"],
                expires_in=3600,
            )
        except SupabaseError:
            log.warning("original signing failed for lead %s", lead["id"])
    try:
        await deliver_branded_result(
            clinic=clinic,
            lead=lead,
            patient_email=user.email,
            before_url=before_url,
            after_url=result_url,
        )
    except Exception:  # noqa: BLE001 - delivery must not roll back the accepted lead
        log.exception("branded delivery failed for lead %s", lead["id"])

    lead["status"] = final_status
    return _lead_out(lead)


def hash_clinic_api_key(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


async def _clinic_from_key(sb, x_clinic_key: str | None) -> dict:
    if not x_clinic_key or len(x_clinic_key) < 32:
        raise HTTPException(status_code=403, detail="invalid_clinic_key")
    rows = await sb.select(
        "clinic_api_keys",
        filters={"key_hash": f"eq.{hash_clinic_api_key(x_clinic_key)}", "status": "eq.active"},
        limit=1,
    )
    if not rows:
        raise HTTPException(status_code=403, detail="invalid_clinic_key")
    credential = rows[0]
    clinics = await sb.select(
        "clinics",
        filters={"id": f"eq.{credential['clinic_id']}", "status": "in.(active,trial)"},
        limit=1,
    )
    if not clinics:
        raise HTTPException(status_code=403, detail="invalid_clinic_key")
    await sb.update(
        "clinic_api_keys",
        filters={"id": f"eq.{credential['id']}"},
        patch={"last_used_at": datetime.now(UTC).isoformat()},
    )
    return clinics[0]


@router.get("/api/clinic/dashboard")
async def clinic_dashboard(x_clinic_key: str | None = Header(default=None)) -> dict:
    sb = get_supabase()
    clinic = await _clinic_from_key(sb, x_clinic_key)
    leads = await sb.select(
        "leads",
        filters={"clinic_id": f"eq.{clinic['id']}", "order": "created_at.desc"},
    )
    return {"clinic": {"id": clinic["id"], "name": clinic["name"]}, "leads": leads}


@router.patch("/api/clinic/leads/{lead_id}")
async def update_lead_status(
    lead_id: str,
    status: str,
    x_clinic_key: str | None = Header(default=None),
) -> dict:
    valid = {"contacted", "booked", "completed", "rejected"}
    if status not in valid:
        raise HTTPException(status_code=422, detail=f"status must be one of {sorted(valid)}")
    sb = get_supabase()
    clinic = await _clinic_from_key(sb, x_clinic_key)
    rows = await sb.select("leads", filters={"id": f"eq.{lead_id}"}, limit=1)
    if not rows or str(rows[0]["clinic_id"]) != str(clinic["id"]):
        raise HTTPException(status_code=404, detail="lead_not_found")
    await sb.update(
        "leads",
        filters={"id": f"eq.{lead_id}"},
        patch={"status": status, "clinic_responded_at": datetime.now(UTC).isoformat()},
    )
    return {"id": lead_id, "status": status}
