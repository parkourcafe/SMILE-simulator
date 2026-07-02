from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_ok():
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["inference_provider"] == "fal_flux_pro_fill"


def test_generate_requires_auth():
    # No Authorization header → 401.
    resp = client.post(
        "/v1/api/generate",
        json={
            "style_id": "00000000-0000-0000-0000-000000000000",
            "original_photo_path": "u/x.png",
        },
    )
    assert resp.status_code == 401
