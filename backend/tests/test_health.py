from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app

client = TestClient(app)


def test_health_ok():
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    # Defaults are mock-first, so the effective provider is the mock.
    assert body["inference_provider"] == "mock"
    assert body["mocks"]["inference"] is True


def test_generate_requires_auth_when_mock_auth_off():
    # With real auth (mock_auth=False), a missing Authorization header → 401.
    app.dependency_overrides[get_settings] = lambda: Settings(mock_auth=False)
    try:
        resp = client.post(
            "/v1/api/generate",
            json={
                "style_id": "00000000-0000-0000-0000-000000000000",
                "original_photo_path": "u/x.png",
            },
        )
        assert resp.status_code == 401
    finally:
        app.dependency_overrides.pop(get_settings, None)
