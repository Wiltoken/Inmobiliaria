"""Email notifications via SMTP for inquiry workflow.

Sends notifications to property owners on new inquiries, and to buyers
when owners respond (accept / decline / request_more_info).
Contact preference (email / phone / both) is respected per REQ-INMO-034.
"""

from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Literal

from app.config import settings

log = logging.getLogger(__name__)

# ── Low-level SMTP ────────────────────────────────────────────────────────────


def _send_smtp_email(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str,
) -> None:
    """Send an email via the configured SMTP server.

    Raises on connection failure so callers can log and continue
    rather than crashing the request.
    """
    if not settings.smtp_host:
        log.warning(
            "smtp_notification_skipped_no_host",
            to=to_email,
            reason="smtp_host not configured",
        )
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = to_email

    part_text = MIMEText(text_body, "plain", "utf-8")
    part_html = MIMEText(html_body, "html", "utf-8")
    msg.attach(part_text)
    msg.attach(part_html)

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.ehlo()
            if settings.smtp_port == 587:
                server.starttls()
            if settings.smtp_user and settings.smtp_password:
                server.login(settings.smtp_user, settings.smtp_password)
            server.sendmail(settings.smtp_from, [to_email], msg.as_string())
        log.info(f"smtp_email_sent to={to_email} subject={subject}")
    except Exception as exc:
        # Log and continue — notifications are best-effort
        log.error(f"smtp_notification_failed to={to_email} error={exc}")


# ── Notification templates ────────────────────────────────────────────────────


def _build_html_email(title: str, body_lines: list[str], cta_link: str | None = None) -> str:
    """Return a basic branded HTML email."""
    cta_block = ""
    if cta_link:
        cta_block = f"""
    <tr>
      <td style="padding: 24px 0 16px;">
        <a href="{cta_link}"
           style="background:#2563eb;color:#fff;padding:12px 24px;
                  text-decoration:none;border-radius:6px;font-weight:600;">
          View Inquiry
        </a>
      </td>
    </tr>"""

    rows = "".join(f'      <tr><td style="padding:4px 0;">{line}</td></tr>\n' for line in body_lines)

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>{title}</title></head>
<body style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:24px;color:#333;">
  <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
    <tr>
      <td style="background:#1e40af;padding:20px;color:#fff;font-size:20px;font-weight:bold;">
        Inmobiliaria Platform
      </td>
    </tr>
    <tr>
      <td style="padding:24px 0 8px;font-size:18px;font-weight:600;">{title}</td>
    </tr>
{rows}
{cta_block}
    <tr>
      <td style="padding:32px 0 0;border-top:1px solid #e5e7eb;margin-top:24px;color:#6b7280;font-size:12px;">
        You received this email because you have an active listing on Inmobiliaria Platform.
        <br>Do not reply directly to this message — use the platform to respond.
      </td>
    </tr>
  </table>
</body>
</html>"""


# ── Public API ────────────────────────────────────────────────────────────────


def send_inquiry_created_notification(
    *,
    buyer_name: str,
    owner_email: str,
    property_title: str,
    inquiry_message: str,
    contact_preference: Literal["email", "phone", "both", "whatsapp", "either"],
    inquiry_id: str | None = None,
) -> None:
    """Notify the property owner that a new inquiry was created.

    Respects ``contact_preference`` — only sends email when
    ``contact_preference`` is ``email`` or ``both``.
    Phone / WhatsApp is out of scope for MVP (logged only).
    """
    if contact_preference not in ("email", "both", "either"):
        log.info(
            "inquiry_notification_skipped_non_email",
            owner=owner_email,
            contact_preference=contact_preference,
        )
        return

    subject = f"New inquiry on your property: {property_title}"
    text_body = f"""You received a new inquiry on "{property_title}".

Buyer: {buyer_name}
Message:
{inquiry_message}

Log in to your dashboard to respond.
"""
    cta_link = None
    if inquiry_id:
        cta_link = f"{settings.app_base_url}/dashboard/inquiries/{inquiry_id}"

    html_body = _build_html_email(
        title=subject,
        body_lines=[
            f"<strong>Property:</strong> {property_title}",
            f"<strong>Buyer:</strong> {buyer_name}",
            f"<strong>Message:</strong><br>{inquiry_message}",
        ],
        cta_link=cta_link,
    )

    _send_smtp_email(owner_email, subject, html_body, text_body)


def send_inquiry_response_notification(
    *,
    owner_name: str,
    buyer_email: str,
    property_title: str,
    action: Literal["accept", "decline", "request_more_info"],
    response_message: str | None,
    contact_preference: Literal["email", "phone", "both", "whatsapp", "either"],
) -> None:
    """Notify the buyer when the property owner responds to their inquiry.

    Sends email when ``contact_preference`` is ``email`` or ``both``.
    """
    if contact_preference not in ("email", "both", "either"):
        log.info(
            "inquiry_response_notification_skipped_non_email",
            buyer=buyer_email,
            contact_preference=contact_preference,
        )
        return

    action_labels = {
        "accept": "is interested in your inquiry",
        "decline": "has declined your inquiry",
        "request_more_info": "has requested more information",
    }
    label = action_labels.get(action, "has responded to your inquiry")

    subject = f"Owner responded: {property_title}"
    text_body = f"""The owner ({owner_name}) {label} on "{property_title}".

"""
    if response_message:
        text_body += f"Message from owner:\n{response_message}\n\n"
    text_body += "Log in to your dashboard to view details and respond.\n"

    html_body = _build_html_email(
        title=subject,
        body_lines=[
            f"<strong>Property:</strong> {property_title}",
            f"<strong>Owner ({owner_name})</strong> {label}.",
        ]
        + ([f"<strong>Owner's message:</strong><br>{response_message}"] if response_message else []),
        cta_link=None,
    )

    _send_smtp_email(buyer_email, subject, html_body, text_body)
