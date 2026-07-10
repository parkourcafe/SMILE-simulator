from __future__ import annotations

import json
import logging
import re
import sys

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import observability
from app.config import Settings
from app.routers import generate


def _test_app() -> FastAPI:
    app = FastAPI()
    observability.install_observability(app)

    @app.get("/ok")
    async def ok() -> dict:
        return {"ok": True}

    @app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("patient_phone=+79991234567")

    return app


def test_request_id_is_echoed_only_when_safe():
    client = TestClient(_test_app())
    client_request_id = "11111111-1111-4111-8111-111111111111"

    accepted = client.get("/ok", headers={"X-Request-ID": client_request_id})
    replaced = client.get("/ok", headers={"X-Request-ID": "../../unsafe"})

    assert accepted.headers["X-Request-ID"] == client_request_id
    generated = replaced.headers["X-Request-ID"]
    assert generated != "../../unsafe"
    assert re.fullmatch(r"[0-9a-f-]{36}", generated)


def test_unhandled_exception_is_captured_but_not_returned(monkeypatch):
    captured = []
    monkeypatch.setattr(observability, "capture_exception", captured.append)
    client = TestClient(_test_app(), raise_server_exceptions=False)

    response = client.get("/boom")

    assert response.status_code == 500
    assert response.json() == {
        "detail": "internal_error",
        "request_id": response.headers["X-Request-ID"],
    }
    assert "+79991234567" not in response.text
    assert isinstance(captured[0], RuntimeError)


def test_sentry_is_opt_in_and_uses_privacy_guards(monkeypatch):
    captured = {}
    monkeypatch.setattr(observability.sentry_sdk, "init", lambda **kwargs: captured.update(kwargs))

    assert observability.configure_sentry(Settings(), release="test@1") is False
    enabled = observability.configure_sentry(
        Settings(sentry_dsn="https://public@sentry.example.test/1", app_env="staging"),
        release="test@1",
    )

    assert enabled is True
    assert captured["send_default_pii"] is False
    assert captured["max_request_body_size"] == "never"
    assert captured["include_local_variables"] is False
    assert captured["traces_sample_rate"] == 0.0


def test_sentry_scrubber_removes_request_and_exception_values():
    event = {
        "user": {"email": "patient@example.test"},
        "extra": {"phone": "+79991234567"},
        "breadcrumbs": {"values": [{"message": "patient@example.test"}]},
        "request": {
            "method": "POST",
            "url": "https://api.example.test/v1/api/leads?phone=%2B79991234567",
            "headers": {"authorization": "Bearer secret"},
            "data": {"phone": "+79991234567"},
        },
        "exception": {
            "values": [
                {
                    "type": "RuntimeError",
                    "value": "patient@example.test",
                    "stacktrace": {"frames": [{"vars": {"token": "secret"}}]},
                }
            ]
        },
    }

    scrubbed = observability.scrub_sentry_event(event, {})

    assert scrubbed["request"] == {
        "method": "POST",
        "url": "https://api.example.test/v1/api/leads",
    }
    assert "user" not in scrubbed
    assert "extra" not in scrubbed
    assert "breadcrumbs" not in scrubbed
    value = scrubbed["exception"]["values"][0]
    assert value["value"] == "RuntimeError"
    assert "vars" not in value["stacktrace"]["frames"][0]


def test_json_logs_do_not_render_exception_values():
    formatter = observability._JsonFormatter()
    try:
        raise RuntimeError("patient@example.test")
    except RuntimeError:
        record = logging.LogRecord(
            "smile.test",
            logging.ERROR,
            __file__,
            1,
            "operation_failed",
            (),
            sys.exc_info(),
        )

    payload = json.loads(formatter.format(record))
    assert payload["message"] == "operation_failed"
    assert payload["error_type"] == "RuntimeError"
    assert "patient@example.test" not in json.dumps(payload)


class _FailingGenerationSupabase:
    def __init__(self) -> None:
        self.patches = []

    async def update(self, _table, *, filters, patch):
        self.patches.append(patch)
        return [patch]

    async def download(self, _path):
        raise RuntimeError("provider leaked patient@example.test")


async def test_generation_persists_only_a_stable_error_code(monkeypatch):
    sb = _FailingGenerationSupabase()
    monkeypatch.setattr(generate, "get_supabase", lambda: sb)
    monkeypatch.setattr(generate, "capture_exception", lambda _exc: None)

    await generate._process(
        "generation-1",
        "user-1",
        "user-1/original.jpg",
        {"prompt_template": "template", "name": "Natural"},
        False,
    )

    assert sb.patches[-1] == {"status": "failed", "error_message": "generation_failed"}
    assert "patient@example.test" not in str(sb.patches)
