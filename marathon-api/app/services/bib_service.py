"""BIB QR code generation and storage."""
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.services import storage_service
from app.utils.qr import generate_qr_png


async def generate_and_store_bib_qr(
    db: AsyncSession,
    registration: object,  # Registration ORM instance — passed in to avoid re-fetch
) -> str:
    """
    Generate a QR code PNG for the registration and upload it to MinIO.

    The QR encodes str(registration.id) — exactly what the volunteer scanner reads.

    Updates registration.qr_code_url in-place (caller must commit).
    Returns the object_name stored in MinIO.
    """
    object_name = f"qr/{registration.id}.png"

    # Generate QR PNG bytes
    png_bytes = generate_qr_png(str(registration.id))

    # Upload to MinIO
    storage_service.upload_file(
        file_bytes=png_bytes,
        object_name=object_name,
        content_type="image/png",
    )

    # Update the ORM object (caller owns the transaction)
    registration.qr_code_url = object_name
    return object_name
