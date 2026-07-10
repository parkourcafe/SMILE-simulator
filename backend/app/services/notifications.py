"""Clinic lead notifications (architecture §8.1–§8.2, CLAUDE.md Phase 5).

A lead is the core B2B product, so delivery must be reliable and observable.
Two channels:

  - WhatsApp Business API (preferred when configured) — the patient-facing template
    from architecture §8.2.
  - Email (MVP fallback) via SMTP.

Both are optional: if a channel isn't configured it is skipped (logged), never raised,
so lead submission never fails just because notifications aren't wired yet. The lead
row is the source of truth and can be re-notified.
"""

from __future__ import annotations

import asyncio
import logging
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage

import httpx

from app.config import Settings, get_settings
from app.observability import capture_exception

log = logging.getLogger("smile.notifications")

# Russian WhatsApp/notification template (architecture §8.2).
LEAD_MESSAGE_RU = (
    "Новый пациент из AI Smile Simulator!\n\n"
    "Имя: {user_name}\n"
    "Тел: {user_phone}\n"
    "Желаемое время: {preferred_time}\n\n"
    "Пациент хочет улучшить улыбку. AI-визуализация приложена.\n\n"
    "Свяжитесь в течение 24 часов для максимальной конверсии."
)


def build_lead_message(lead: dict) -> str:
    """Render the clinic-facing message body for a lead."""
    return LEAD_MESSAGE_RU.format(
        user_name=lead.get("user_name", "—"),
        user_phone=lead.get("user_phone", "—"),
        preferred_time=lead.get("preferred_time") or "не указано",
    )


@dataclass
class NotifyResult:
    channel: str  # "whatsapp" | "email" | "skipped"
    ok: bool
    detail: str = ""


def _send_email_sync(settings: Settings, to_email: str, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["From"] = settings.smtp_from
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as server:
        if settings.smtp_use_tls:
            server.starttls()
        if settings.smtp_user:
            server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(msg)


async def _send_email(settings: Settings, to_email: str, body: str) -> NotifyResult:
    if not settings.smtp_host or not to_email:
        return NotifyResult("email", False, "smtp_or_recipient_unconfigured")
    try:
        # smtplib is blocking — run it off the event loop.
        await asyncio.to_thread(
            _send_email_sync, settings, to_email, "Новый пациент — AI Smile Simulator", body
        )
        return NotifyResult("email", True)
    except Exception as exc:  # noqa: BLE001 - notification failure must not break the lead
        capture_exception(exc)
        log.warning(
            "clinic_email_failed",
            extra={"event": "clinic_email_failed", "error_type": type(exc).__name__},
        )
        return NotifyResult("email", False, "delivery_failed")


async def _send_whatsapp(settings: Settings, to_phone: str, body: str) -> NotifyResult:
    if not settings.whatsapp_token or not settings.whatsapp_phone_id or not to_phone:
        return NotifyResult("whatsapp", False, "whatsapp_unconfigured")
    url = f"{settings.whatsapp_api_base}/{settings.whatsapp_phone_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone.lstrip("+"),
        "type": "text",
        "text": {"body": body},
    }
    headers = {"Authorization": f"Bearer {settings.whatsapp_token}"}
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code >= 400:
            return NotifyResult("whatsapp", False, f"provider_http_{resp.status_code}")
        return NotifyResult("whatsapp", True)
    except Exception as exc:  # noqa: BLE001
        capture_exception(exc)
        log.warning(
            "clinic_whatsapp_failed",
            extra={"event": "clinic_whatsapp_failed", "error_type": type(exc).__name__},
        )
        return NotifyResult("whatsapp", False, "delivery_failed")


async def notify_clinic(clinic: dict, lead: dict, result_url: str | None = None) -> NotifyResult:
    """Notify a clinic of a new lead. Prefers WhatsApp, falls back to email.

    Returns a NotifyResult describing what happened (never raises on delivery failure).
    """
    settings = get_settings()
    body = build_lead_message(lead)
    if result_url:
        body += f"\n\nРезультат: {result_url}"

    # Prefer WhatsApp to the clinic's contact phone.
    wa = await _send_whatsapp(settings, clinic.get("phone", ""), body)
    if wa.ok:
        return wa

    email = await _send_email(settings, clinic.get("email", ""), body)
    if email.ok:
        return email

    # Nothing configured/worked — log so the lead can be followed up manually.
    log.error(
        "clinic_notification_not_delivered",
        extra={
            "event": "clinic_notification_not_delivered",
            "lead_id": lead.get("id"),
            "clinic_id": clinic.get("id"),
        },
    )
    return NotifyResult("skipped", False, f"wa={wa.detail}; email={email.detail}")
