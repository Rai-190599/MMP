import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.registration import Registration, RegistrationStatus
from app.models.user import User
from app.services import storage_service

router = APIRouter(prefix="/certificates", tags=["certificates"])


@router.get("/{registration_id}")
async def get_certificate(
    registration_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    """
    Get a presigned download URL for the participant's certificate.

    Returns:
        200 { download_url, expires_in } — certificate is ready
        202 { message }                  — still being generated
    """
    result = await db.execute(
        select(Registration).where(Registration.id == registration_id)
    )
    reg = result.scalar_one_or_none()

    if reg is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registration not found")

    # Ownership check — participant must own this registration
    if reg.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your registration")

    if reg.status != RegistrationStatus.finished_certified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Certificate only available after finishing the race",
        )

    # Certificate not yet generated — Celery task still running
    if reg.certificate_url is None:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={"message": "Certificate is being generated, try again shortly"},
        )

    # Generate a 1-hour presigned URL on demand
    download_url = storage_service.get_presigned_url(
        reg.certificate_url, expires_in_seconds=3600
    )

    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"download_url": download_url, "expires_in": 3600},
    )
