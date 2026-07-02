"""B2B lead submission + clinic-side endpoints (architecture §4.5, §8).

A lead is the core B2B product: it carries the patient's selfie + AI result + contact,
so the clinic sees what the patient wants before calling. Clinics are notified via
WhatsApp (preferred) or email — see app/services/notifications.py.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Header, HTTPException

from app.deps import CurrentUser, get_current_user
from app.schemas import LeadOut, LeadRequest
from app.services.branded_delivery import deliver_branded_result
from app.services.notifications import notify_clinic
from app.services.supabase_client import get_supabase

router = APIRouter(tags=["leads"])
log = logging.getLogger("smile.leads")


@router.post("/api/leads", response_model=LeadOut, status_code=201)
async def submit_lead(body: LeadRequest, user: CurrentUser = Depends(get_current_user)) -> LeadOut:
    sb = get_supabase()

    clinics = await sb.select("clinics", filters={"id": f"eq.{body.clinic_id}"}, limit=1)
    if not clinics:
        raise HTTPException(status_code=404, detail="clinic_not_found")
    clinic = clinics[0]

    gens = await sb.select("generations", filters={"id": f"eq.{body.generation_id}"}, limit=1)
    if not gens or gens[0]["user_id"] != user.id:
        raise HTTPException(status_code=404, detail="generation_not_found")

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
        },
    )

    result_url = None
    if gens[0].get("result_photo_url"):
        try:
            result_url = await sb.create_signed_url(gens[0]["result_photo_url"], expires_in=86400)
        except Exception:  # noqa: BLE001
            result_url = None

    notice = await notify_clinic(clinic, lead, result_url)
    # Only advance to "notified" if a channel actually delivered; otherwise leave "new"
    # so it surfaces for manual follow-up.
    final_status = "notified" if notice.ok else "new"
    patch: dict = {"status": final_status}
    if notice.ok:
        patch["clinic_notified_at"] = "now()"
    await sb.update("leads", filters={"id": f"eq.{lead['id']}"}, patch=patch)

    # Branded result delivery (v1.1): the patient gets their before/after under the
    # chosen clinic's brand. Best-effort — never fails the lead.
    before_url = None
    if gens[0].get("original_photo_url"):
        try:
            before_url = await sb.create_signed_url(gens[0]["original_photo_url"], expires_in=86400)
        except Exception:  # noqa: BLE001
            before_url = None
    try:
        await deliver_branded_result(
            clinic=clinic,
            lead=lead,
            patient_email=user.email,
            before_url=before_url,
            after_url=result_url,
        )
    except Exception:  # noqa: BLE001 - branded delivery must not break lead submission
        log.warning("branded delivery raised for lead %s", lead["id"])

    return LeadOut(
        id=lead["id"],
        clinic_id=lead["clinic_id"],
        status=final_status,
        created_at=lead.get("created_at"),
    )


# --- Clinic-facing (B2B) endpoints; auth via clinic API key -----------------
async def _clinic_from_key(sb, x_clinic_key: str | None) -> dict:
    if not x_clinic_key:
        raise HTTPException(status_code=403, detail="clinic_key_required")
    # TODO(phase-2): proper clinic API keys table. MVP maps key == clinic id.
    rows = await sb.select("clinics", filters={"id": f"eq.{x_clinic_key}"}, limit=1)
    if not rows:
        raise HTTPException(status_code=403, detail="invalid_clinic_key")
    return rows[0]


@router.get("/api/clinic/dashboard")
async def clinic_dashboard(x_clinic_key: str | None = Header(default=None)) -> dict:
    sb = get_supabase()
    clinic = await _clinic_from_key(sb, x_clinic_key)
    leads = await sb.select(
        "leads", filters={"clinic_id": f"eq.{clinic['id']}", "order": "created_at.desc"}
    )
    return {"clinic": {"id": clinic["id"], "name": clinic["name"]}, "leads": leads}


@router.patch("/api/clinic/leads/{lead_id}")
async def update_lead_status(
    lead_id: str, status: str, x_clinic_key: str | None = Header(default=None)
) -> dict:
    valid = {"contacted", "booked", "completed", "rejected"}
    if status not in valid:
        raise HTTPException(status_code=422, detail=f"status must be one of {sorted(valid)}")
    sb = get_supabase()
    clinic = await _clinic_from_key(sb, x_clinic_key)
    rows = await sb.select("leads", filters={"id": f"eq.{lead_id}"}, limit=1)
    if not rows or rows[0]["clinic_id"] != clinic["id"]:
        raise HTTPException(status_code=404, detail="lead_not_found")
    await sb.update(
        "leads",
        filters={"id": f"eq.{lead_id}"},
        patch={"status": status, "clinic_responded_at": "now()"},
    )
    return {"id": lead_id, "status": status}
