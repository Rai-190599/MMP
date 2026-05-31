"""
Notification service — real email/WhatsApp delivery with stub fallback.

Behavior is controlled by environment variables:
- Email:    SMTP_HOST set → real smtplib send; else → log stub
- WhatsApp: TWILIO_ACCOUNT_SID + TWILIO_AUTH_TOKEN + TWILIO_WHATSAPP_FROM set → Twilio; else → log stub

All functions are synchronous (called from Celery workers).
"""
import logging
import smtplib
from datetime import datetime, timezone
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------

def send_email(
    to_email: str,
    subject: str,
    body_html: str,
    attachment_bytes: Optional[bytes] = None,
    attachment_filename: Optional[str] = None,
) -> bool:
    """
    Send an HTML email with an optional binary attachment (e.g. PDF certificate).

    Returns True on success, False on failure (never raises).
    """
    if not settings.SMTP_HOST:
        logger.info("[EMAIL STUB] To: %s, Subject: %s, Attachment: %s",
                    to_email, subject, attachment_filename or "none")
        return True

    from_addr = settings.SMTP_FROM_EMAIL or settings.SMTP_FROM or settings.SMTP_USER or "noreply@example.com"

    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_email

    # HTML body
    msg.attach(MIMEText(body_html, "html", "utf-8"))

    # Optional attachment
    if attachment_bytes and attachment_filename:
        part = MIMEApplication(attachment_bytes, Name=attachment_filename)
        part["Content-Disposition"] = f'attachment; filename="{attachment_filename}"'
        msg.attach(part)

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
            server.ehlo()
            if settings.SMTP_PORT != 465:
                server.starttls()
                server.ehlo()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(from_addr, [to_email], msg.as_string())
        logger.info("Email sent to %s — subject: %s", to_email, subject)
        return True
    except Exception as exc:
        logger.error("Failed to send email to %s: %s", to_email, exc)
        return False


# ---------------------------------------------------------------------------
# WhatsApp (Twilio)
# ---------------------------------------------------------------------------

def send_whatsapp(to_phone: str, message: str) -> bool:
    """
    Send a WhatsApp message via Twilio.

    Returns True on success, False on failure (never raises).
    """
    if not (settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN and settings.TWILIO_WHATSAPP_FROM):
        logger.info("[WHATSAPP STUB] To: %s, Message: %s", to_phone, message)
        return True

    try:
        from twilio.rest import Client  # type: ignore[import]
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        client.messages.create(
            from_=f"whatsapp:{settings.TWILIO_WHATSAPP_FROM}",
            to=f"whatsapp:{to_phone}",
            body=message,
        )
        logger.info("WhatsApp sent to %s", to_phone)
        return True
    except Exception as exc:
        logger.error("Failed to send WhatsApp to %s: %s", to_phone, exc)
        return False
