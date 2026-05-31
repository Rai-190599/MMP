"""Certificate PDF generation and storage."""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.registration import Registration
from app.services import storage_service
from app.utils.pdf import generate_certificate_pdf


async def generate_and_store_certificate(
    db: AsyncSession,
    registration_id: uuid.UUID,
) -> str:
    """
    Fetch registration + user + event, generate a PDF certificate, upload to MinIO,
    and persist the object_name on the registration row.

    Returns the object_name.
    """
    # Single joined query — registration → user + event
    result = await db.execute(
        select(Registration)
        .options(
            selectinload(Registration.user),
            selectinload(Registration.event),
        )
        .where(Registration.id == registration_id)
    )
    reg = result.scalar_one()

    pdf_bytes = generate_certificate_pdf(
        participant_name=reg.user.name,
        bib_number=reg.bib_number or "N/A",
        distance=reg.distance or "N/A",
        finish_time=reg.finish_time,
        event_name=reg.event.name,
        event_date=reg.event.event_date,
        location=reg.event.location or "",
    )

    object_name = f"certificates/{registration_id}.pdf"
    storage_service.upload_file(
        file_bytes=pdf_bytes,
        object_name=object_name,
        content_type="application/pdf",
    )

    reg.certificate_url = object_name
    await db.commit()
    return object_name
