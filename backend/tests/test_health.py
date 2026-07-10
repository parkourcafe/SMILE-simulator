import hashlib

from fastapi.testclient import TestClient

from app import main
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


def test_readiness_checks_supabase_and_face_model(monkeypatch, tmp_path):
    class Supabase:
        async def ping(self):
            return None

    model = tmp_path / "model.task"
    model.write_bytes(b"ready")
    settings = Settings(
        mock_inference=False,
        supabase_url="https://project.supabase.co",
        supabase_secret_key="sb_secret_test",
        mediapipe_face_model=str(model),
        mediapipe_face_model_sha256=hashlib.sha256(b"ready").hexdigest(),
    )
    monkeypatch.setattr(main, "settings", settings)
    monkeypatch.setattr(main, "get_supabase", lambda: Supabase())

    resp = client.get("/ready")

    assert resp.status_code == 200
    assert resp.json() == {
        "status": "ready",
        "checks": {"supabase": "ok", "face_model": "ok"},
    }


def test_readiness_returns_503_without_dependencies(monkeypatch):
    class Supabase:
        async def ping(self):
            raise main.SupabaseError("unavailable")

    monkeypatch.setattr(main, "settings", Settings(mock_inference=True))
    monkeypatch.setattr(main, "get_supabase", lambda: Supabase())

    resp = client.get("/ready")

    assert resp.status_code == 503
    assert resp.json()["checks"]["supabase"] == "unavailable"


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
