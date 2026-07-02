"""price_estimates endpoint (v1.1 cost anchor) with a stubbed Supabase client."""

from __future__ import annotations

from fastapi.testclient import TestClient

import app.routers.price_estimates as pe
from app.main import app

client = TestClient(app)

_ROW = {
    "id": "11111111-1111-1111-1111-111111111111",
    "city": "Moscow",
    "style_id": "22222222-2222-2222-2222-222222222222",
    "treatment_label": "Professional whitening",
    "treatment_label_ru": "Профессиональное отбеливание",
    "price_min": 8000,
    "price_max": 25000,
    "currency": "RUB",
    "is_estimate": True,
}


class _FakeSupabase:
    def __init__(self):
        self.last_filters = None

    async def select(self, table, *, filters=None, limit=None):
        assert table == "price_estimates"
        self.last_filters = filters
        return [_ROW]


def test_price_estimates_returns_range(monkeypatch):
    fake = _FakeSupabase()
    monkeypatch.setattr(pe, "get_supabase", lambda: fake)

    resp = client.get("/v1/api/price-estimates", params={"city": "Moscow"})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["currency"] == "RUB"
    assert body[0]["price_min"] == 8000
    assert body[0]["price_max"] == 25000
    assert body[0]["is_estimate"] is True
    # city filter is forwarded to PostgREST
    assert fake.last_filters["city"] == "eq.Moscow"
