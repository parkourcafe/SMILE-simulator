import pytest

from app.services import notifications


def test_build_lead_message_fills_template():
    lead = {"user_name": "Анна", "user_phone": "+79991234567", "preferred_time": "morning"}
    msg = notifications.build_lead_message(lead)
    assert "Анна" in msg
    assert "+79991234567" in msg
    assert "morning" in msg
    assert msg.startswith("Новый пациент")


def test_build_lead_message_handles_missing_time():
    msg = notifications.build_lead_message({"user_name": "X", "user_phone": "Y"})
    assert "не указано" in msg


@pytest.mark.asyncio
async def test_notify_clinic_skips_when_unconfigured():
    # No SMTP/WhatsApp env in tests → both channels skipped, no exception, ok=False.
    clinic = {"id": "c1", "phone": "+79990000000", "email": "clinic@example.com"}
    lead = {"id": "l1", "user_name": "A", "user_phone": "+7000", "preferred_time": None}
    result = await notifications.notify_clinic(clinic, lead, result_url="https://x/y.png")
    assert result.ok is False
    assert result.channel == "skipped"


@pytest.mark.asyncio
async def test_whatsapp_preferred_when_configured(monkeypatch):
    async def fake_wa(settings, phone, body):
        return notifications.NotifyResult("whatsapp", True)

    monkeypatch.setattr(notifications, "_send_whatsapp", fake_wa)
    res = await notifications.notify_clinic(
        {"id": "c", "phone": "+7", "email": "e@x"}, {"id": "l", "user_name": "n", "user_phone": "p"}
    )
    assert res.channel == "whatsapp" and res.ok
