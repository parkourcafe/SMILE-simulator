"""Admin endpoints (architecture §4.6). Guarded by a static admin API key."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.deps import require_admin
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
