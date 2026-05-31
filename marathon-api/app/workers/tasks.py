"""
Celery tasks for notifications and certificate generation.

send_email_task / send_whatsapp_task delegate to notification_service,
which handles real delivery vs stub based on env vars.
Signatures are unchanged from Sprint 2/3/4 — all callers remain unaffected.
"""
import logging
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.models.notification import Notification, NotificationChannel, NotificationTriggerType
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Synchronous DB session for Celery workers
# ---------------------------------------------------------------------------
_sync_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
_sync_engine = create_engine(_sync_url, pool_pre_ping=True, pool_size=5)
_SyncSession = sessionmaker(bind=_sync_engine, autocommit=False, autoflush=False)


def _get_sync_db() -> Session:
    return _SyncSession()


def _record_notification(
    db: Session,
    registration_id: str,
    channel: NotificationChannel,
    trigger_type: NotificationTriggerType,
    content: str,
    sent: bool,
) -> None:
    """Persist a Notification row."""
    import uuid
    notif = Notification(
        registration_id=uuid.UUID(registration_id),
        channel=channel,
        trigger_type=trigger_type,
        content=content,
        sent=sent,
        sent_at=datetime.now(timezone.utc) if sent else None,
    )
    db.add(notif)
    db.commit()


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

@celery_app.task(name="app.workers.tasks.send_email_task", bind=True, max_retries=3)
def send_email_task(
    self,
    to_email: str,
    subject: str,
    body_html: str,
    registration_id: str | None = None,
) -> dict:
    """Send (or stub) an HTML email and record a Notification row."""
    from app.services.notification_service import send_email
    sent = send_email(to_email=to_email, subject=subject, body_html=body_html)

    if registration_id:
        db = _get_sync_db()
        try:
            _record_notification(
                db,
                registration_id=registration_id,
                channel=NotificationChannel.email,
                trigger_type=NotificationTriggerType.status_change,
                content=f"Subject: {subject}\n\n{body_html}",
                sent=sent,
            )
        except Exception as exc:
            logger.error("Failed to record email notification: %s", exc)
        finally:
            db.close()

    return {"status": "sent" if sent else "failed", "to": to_email, "subject": subject}


@celery_app.task(name="app.workers.tasks.send_whatsapp_task", bind=True, max_retries=3)
def send_whatsapp_task(
    self,
    to_phone: str,
    message: str,
    registration_id: str | None = None,
) -> dict:
    """Send (or stub) a WhatsApp message and record a Notification row."""
    from app.services.notification_service import send_whatsapp
    sent = send_whatsapp(to_phone=to_phone, message=message)

    if registration_id:
        db = _get_sync_db()
        try:
            _record_notification(
                db,
                registration_id=registration_id,
                channel=NotificationChannel.whatsapp,
                trigger_type=NotificationTriggerType.status_change,
                content=message,
                sent=sent,
            )
        except Exception as exc:
            logger.error("Failed to record whatsapp notification: %s", exc)
        finally:
            db.close()

    return {"status": "sent" if sent else "failed", "to": to_phone}


@celery_app.task(name="app.workers.tasks.generate_certificate_task", bind=True, max_retries=3)
def generate_certificate_task(self, registration_id: str) -> dict:
    """
    Generate a PDF certificate and upload to MinIO.
    After upload, dispatches a certificate-ready email with a 7-day presigned URL.
    """
    import asyncio
    import uuid as _uuid

    logger.info("📄 Generating certificate for registration %s", registration_id)

    try:
        from app.database import AsyncSessionLocal
        from app.services.certificate_service import generate_and_store_certificate
        from app.services.storage_service import get_presigned_url

        reg_uuid = _uuid.UUID(registration_id)

        async def _run():
            async with AsyncSessionLocal() as db:
                return await generate_and_store_certificate(db, reg_uuid)

        object_name = asyncio.run(_run())
        logger.info("✅ Certificate stored at '%s'", object_name)

        presigned_url = get_presigned_url(object_name, expires_in_seconds=7 * 24 * 3600)

        db_sync = _get_sync_db()
        try:
            from app.models.registration import Registration
            from app.models.user import User
            from sqlalchemy import select as _select
            from sqlalchemy.orm import selectinload as _selectinload

            reg = db_sync.execute(
                _select(Registration)
                .options(_selectinload(Registration.user))
                .where(Registration.id == reg_uuid)
            ).scalar_one_or_none()

            if reg and reg.user:
                # Fetch PDF bytes from MinIO to attach to the email
                pdf_bytes: bytes | None = None
                try:
                    import io
                    from app.services.storage_service import _s3, BUCKET
                    buf = io.BytesIO()
                    _s3.download_fileobj(BUCKET, object_name, buf)
                    pdf_bytes = buf.getvalue()
                except Exception as pdf_exc:
                    logger.warning("Could not fetch PDF for attachment: %s", pdf_exc)

                filename = f"certificate_{reg.bib_number or reg_uuid}.pdf"

                from app.services.notification_service import send_email
                sent = send_email(
                    to_email=reg.user.email,
                    subject="🏅 Your marathon certificate is ready!",
                    body_html=(
                        f"Hi {reg.user.name},<br><br>"
                        f"Congratulations on completing the race! 🎉<br><br>"
                        f"Your completion certificate is attached to this email.<br>"
                        f"You can also <a href='{presigned_url}'>download it here</a> (link valid 7 days).<br><br>"
                        f"Well done!"
                    ),
                    attachment_bytes=pdf_bytes,
                    attachment_filename=filename,
                )
                logger.info("Certificate email sent to %s (attachment: %s)", reg.user.email, "yes" if pdf_bytes else "no")
        finally:
            db_sync.close()

        return {"status": "done", "object_name": object_name}

    except Exception as exc:
        logger.error("Certificate generation failed for %s: %s", registration_id, exc)
        raise self.retry(exc=exc, countdown=30)


@celery_app.task(name="app.workers.tasks.send_broadcast_task", bind=True, max_retries=3)
def send_broadcast_task(
    self,
    registration_id: str,
    channel: str,
    subject: str,
    message: str,
) -> dict:
    """
    Send a manual broadcast notification to a single recipient.
    Called once per recipient from the broadcast endpoint.
    """
    import uuid as _uuid
    from app.models.notification import NotificationChannel, NotificationTriggerType

    db = _get_sync_db()
    try:
        from app.models.registration import Registration
        from app.models.user import User
        from sqlalchemy import select as _select
        from sqlalchemy.orm import selectinload as _selectinload

        reg = db.execute(
            _select(Registration)
            .options(_selectinload(Registration.user))
            .where(Registration.id == _uuid.UUID(registration_id))
        ).scalar_one_or_none()

        if reg is None or reg.user is None:
            logger.warning("Broadcast: registration %s not found or has no user", registration_id)
            return {"status": "skipped"}

        ch = NotificationChannel(channel)
        sent = False

        if ch == NotificationChannel.email:
            from app.services.notification_service import send_email
            sent = send_email(to_email=reg.user.email, subject=subject, body_html=message)
        elif ch == NotificationChannel.whatsapp:
            from app.services.notification_service import send_whatsapp
            phone = getattr(reg.user, "phone", None) or ""
            if phone:
                sent = send_whatsapp(to_phone=phone, message=message)
            else:
                logger.warning("Broadcast: user %s has no phone number", reg.user.id)

        _record_notification(
            db,
            registration_id=registration_id,
            channel=ch,
            trigger_type=NotificationTriggerType.manual_broadcast,
            content=f"Subject: {subject}\n\n{message}" if ch == NotificationChannel.email else message,
            sent=sent,
        )

        return {"status": "sent" if sent else "failed"}

    except Exception as exc:
        logger.error("Broadcast task failed for %s: %s", registration_id, exc)
        raise self.retry(exc=exc, countdown=15)
    finally:
        db.close()
