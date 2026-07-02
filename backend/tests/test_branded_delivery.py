"""Branded result delivery (v1.1): HTML render + artifact fallback in dev/mock."""

from __future__ import annotations

import pytest

from app.services.branded_delivery import deliver_branded_result, render_branded_html


def test_render_branded_html_has_clinic_and_images():
    html = render_branded_html(
        clinic_name="Клиника Улыбка",
        logo_url=None,
        before_url="https://x/before.png",
        after_url="https://x/after.png",
    )
    assert "Клиника Улыбка" in html
    assert "before.png" in html
    assert "after.png" in html
    # medical disclaimer is present on the patient-facing artifact
    assert "не медицинская рекомендация" in html


@pytest.mark.asyncio
async def test_deliver_writes_artifact_when_no_smtp(tmp_path, monkeypatch):
    # No SMTP configured (default) -> renders to an artifact file under artifacts_dir.
    monkeypatch.setenv("ARTIFACTS_DIR", str(tmp_path))
    # get_settings is cached; clear it so the env override takes effect.
    from app.config import get_settings

    get_settings.cache_clear()
    try:
        result = await deliver_branded_result(
            clinic={"id": "c1", "name": "Клиника Улыбка", "logo_url": None},
            lead={"id": "lead-123"},
            patient_email="patient@example.com",  # no SMTP host -> still artifact
            before_url="https://x/before.png",
            after_url="https://x/after.png",
        )
        assert result.ok
        assert result.channel == "artifact"
        written = tmp_path / "branded" / "lead-123.html"
        assert written.exists()
        assert "Клиника Улыбка" in written.read_text(encoding="utf-8")
    finally:
        get_settings.cache_clear()
