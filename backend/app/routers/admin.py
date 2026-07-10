"""Admin endpoints (architecture §4.6). Guarded by a static admin API key."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException

from app.deps import require_admin
from app.routers.leads import hash_clinic_api_key
from app.services.supabase_client import get_supabase

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("/stats")
async def stats() -> dict:
    """Aggregate counts/cost/revenue/leads for the ops dashboard."""
    sb = get_supabase()
    generations = await sb.select("generations", limit=10000)
    leads = await sb.select("leads", limit=10000)
    payments = await sb.select("payments", filters={"status": "eq.completed"}, limit=10000)

    completed = [g for g in generations if g["status"] == "completed"]
    total_cost = sum(float(g.get("inference_cost_usd") or 0) for g in generations)
    revenue = sum(float(p.get("amount") or 0) for p in payments)
    return {
        "generations_total": len(generations),
        "generations_completed": len(completed),
        "success_rate": round(len(completed) / len(generations), 3) if generations else 0,
        "total_inference_cost_usd": round(total_cost, 2),
        "leads_total": len(leads),
        "revenue_completed": round(revenue, 2),
    }


@router.get("/generations")
async def list_generations(limit: int = 100) -> list[dict]:
    sb = get_supabase()
    return await sb.select("generations", filters={"order": "created_at.desc"}, limit=limit)


@router.post("/styles")
async def upsert_style(style: dict) -> dict:
    sb = get_supabase()
    if style.get("id"):
        rows = await sb.update("styles", filters={"id": f"eq.{style['id']}"}, patch=style)
        return rows[0] if rows else {}
    return await sb.insert("styles", style)


@router.post("/clinics")
async def upsert_clinic(clinic: dict) -> dict:
    sb = get_supabase()
    if clinic.get("id"):
        rows = await sb.update("clinics", filters={"id": f"eq.{clinic['id']}"}, patch=clinic)
        return rows[0] if rows else {}
    return await sb.insert("clinics", clinic)


@router.post("/clinics/{clinic_id}/keys", status_code=201)
async def create_clinic_key(clinic_id: str, label: str | None = None) -> dict:
    """Create a revocable clinic credential and return the plaintext once."""
    if label is not None and not 1 <= len(label.strip()) <= 120:
        raise HTTPException(status_code=422, detail="invalid_label")
    sb = get_supabase()
    clinics = await sb.select("clinics", filters={"id": f"eq.{clinic_id}"}, limit=1)
    if not clinics:
        raise HTTPException(status_code=404, detail="clinic_not_found")

    plaintext = f"zlk_{secrets.token_urlsafe(32)}"
    row = await sb.insert(
        "clinic_api_keys",
        {
            "clinic_id": clinic_id,
            "key_hash": hash_clinic_api_key(plaintext),
            "label": label.strip() if label else None,
            "status": "active",
        },
    )
    return {
        "id": row["id"],
        "clinic_id": clinic_id,
        "label": row.get("label"),
        "key": plaintext,
    }


@router.post("/clinic-keys/{key_id}/revoke")
async def revoke_clinic_key(key_id: str) -> dict:
    sb = get_supabase()
    rows = await sb.update(
        "clinic_api_keys",
        filters={"id": f"eq.{key_id}", "status": "eq.active"},
        patch={"status": "revoked", "revoked_at": datetime.now(UTC).isoformat()},
    )
    if not rows:
        raise HTTPException(status_code=404, detail="clinic_key_not_found")
    return {"id": key_id, "status": "revoked"}
