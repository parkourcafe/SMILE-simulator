"""Branded result delivery (v1.1, architecture §8 / AGENT_PROMPT Phase 5).

Within ~1 minute of a lead, the patient receives their before/after under the
CHOSEN CLINIC's brand ("Клиника X получила вашу заявку, вот ваша визуализация").
This reinforces the hand-off and makes the clinic look proactive.

Delivery is best-effort and never breaks lead submission:
  - SMTP configured + patient email known  → send a real branded HTML email.
  - otherwise (dev / mock)                  → render the HTML to an artifact file
    under ``settings.artifacts_dir`` so the template is inspectable end-to-end.
"""

from __future__ import annotations

import asyncio
import logging
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path

from app.config import Settings, get_settings

log = logging.getLogger("smile.branded")

BRANDED_SUBJECT_RU = "Ваша визуализация улыбки — {clinic_name}"


def render_branded_html(
    *, clinic_name: str, logo_url: str | None, before_url: str | None, after_url: str | None
) -> str:
    """Render the patient-facing branded email (RU). Merge fields only — no logic."""
    logo = (
        f'<img src="{logo_url}" alt="{clinic_name}" style="max-height:48px;margin-bottom:16px">'
        if logo_url
        else f'<h2 style="margin:0 0 16px">{clinic_name}</h2>'
    )
    before = (
        f'<img src="{before_url}" alt="До" style="width:48%;border-radius:8px">'
        if before_url
        else '<div style="width:48%">—</div>'
    )
    after = (
        f'<img src="{after_url}" alt="После" style="width:48%;border-radius:8px">'
        if after_url
        else '<div style="width:48%">—</div>'
    )
    body_style = "font-family:Arial,sans-serif;color:#1a1a1a;max-width:560px;margin:auto"
    return f"""<!doctype html>
<html lang="ru"><body style="{body_style}">
  {logo}
  <p><b>Клиника {clinic_name}</b> получила вашу заявку — вот ваша визуализация улыбки.</p>
  <div style="display:flex;justify-content:space-between;gap:4%">{before}{after}</div>
  <p style="color:#666;font-size:13px;margin-top:16px">
    Это визуализация, а не медицинская рекомендация. Клиника свяжется с вами в ближайшее время.
  </p>
  <p style="color:#999;font-size:12px">AI Smile Simulator</p>
</body></html>"""


@dataclass
class BrandedDeliveryResult:
    ok: bool
    channel: str  # "email" | "artifact" | "skipped"
    detail: str = ""


def _write_artifact(settings: Settings, lead_id: str, html: str) -> Path:
    out_dir = Path(settings.artifacts_dir) / "branded"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{lead_id}.html"
    path.write_text(html, encoding="utf-8")
    return path


def _send_html_email_sync(settings: Settings, to_email: str, subject: str, html: str) -> None:
    # HTML alternative (notifications._send_email_sync sends plain text only).
    msg = EmailMessage()
    msg["From"] = settings.smtp_from
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content("Ваша визуализация улыбки — откройте письмо в HTML-формате.")
    msg.add_alternative(html, subtype="html")
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as server:
        if settings.smtp_use_tls:
            server.starttls()
        if settings.smtp_user:
            server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(msg)


async def deliver_branded_result(
    *,
    clinic: dict,
    lead: dict,
    patient_email: str | None,
    before_url: str | None,
    after_url: str | None,
) -> BrandedDeliveryResult:
    settings = get_settings()
    clinic_name = clinic.get("name", "клиника")
    html = render_branded_html(
        clinic_name=clinic_name,
        logo_url=clinic.get("logo_url"),
        before_url=before_url,
        after_url=after_url,
    )
    subject = BRANDED_SUBJECT_RU.format(clinic_name=clinic_name)
    lead_id = str(lead.get("id", "unknown"))

    if settings.smtp_host and patient_email:
        try:
            await asyncio.to_thread(_send_html_email_sync, settings, patient_email, subject, html)
            log.info("branded_result_sent lead=%s channel=email", lead_id)
            return BrandedDeliveryResult(True, "email")
        except Exception as exc:  # noqa: BLE001 - never break the lead
            log.warning("branded email failed for lead %s: %s", lead_id, exc)

    # Dev / mock: render to a file so the template is verifiable without SMTP.
    try:
        path = await asyncio.to_thread(_write_artifact, settings, lead_id, html)
        log.info("branded_result_sent lead=%s channel=artifact path=%s", lead_id, path)
        return BrandedDeliveryResult(True, "artifact", str(path))
    except Exception as exc:  # noqa: BLE001
        log.warning("branded artifact write failed for lead %s: %s", lead_id, exc)
        return BrandedDeliveryResult(False, "skipped", str(exc)[:200])
