import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.event import Event
from app.models.user import User
from app.schemas.registration import EventRegistrationRequest, RegistrationCreate, RegistrationOut, StatusPageOut
from app.services import registration_service
from app.services import storage_service
from app.workers.tasks import send_email_task, send_whatsapp_task

router = APIRouter(prefix="/registrations", tags=["registrations"])


@router.post("/", response_model=RegistrationOut, status_code=status.HTTP_201_CREATED)
async def create_registration(
    body: RegistrationCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RegistrationOut:
    """Participant registers for an event."""
    if current_user.role.value != "participant":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only participants can register for events",
        )

    reg = await registration_service.create_registration(db, current_user.id, body)

    # Dispatch welcome email (stub in Sprint 2)
    send_email_task.delay(
        to_email=current_user.email,
        subject=f"Registration confirmed - {reg.event_id}",
        body_html=(
            f"Hi {current_user.name},<br><br>"
            f"Your registration has been confirmed.<br>"
            f"Distance: {reg.distance or 'TBD'}<br>"
            f"BIB: TBD<br><br>"
            f"See you at the race!"
        ),
        registration_id=str(reg.id),
    )

    return RegistrationOut.model_validate(reg)


@router.post("/join", response_model=RegistrationOut, status_code=status.HTTP_201_CREATED)
async def join_event(
    body: EventRegistrationRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RegistrationOut:
    """Participant joins an active event."""
    if current_user.role.value != "participant":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only participants can register for events",
        )

    event_result = await db.execute(select(Event).where(Event.id == body.event_id))
    event = event_result.scalar_one_or_none()
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event '{body.event_id}' not found",
        )
    if not event.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Event is inactive",
        )

    reg = await registration_service.create_registration(
        db,
        current_user.id,
        RegistrationCreate(
            event_id=body.event_id,
            distance=body.distance,
            tshirt_size=body.tshirt_size,
            emergency_contact=body.emergency_contact,
        ),
    )

    send_email_task.delay(
        to_email=current_user.email,
        subject=f"Registration confirmed - {reg.event_id}",
        body_html=(
            f"Hi {current_user.name},<br><br>"
            f"Your registration has been confirmed.<br>"
            f"Distance: {reg.distance}<br>"
            f"BIB: TBD<br><br>"
            f"See you at the race!"
        ),
        registration_id=str(reg.id),
    )

    return RegistrationOut.model_validate(reg)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_registration(
    event_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """
    Participant cancels their own registration for an event.
    Only allowed when status is 'registered' or 'approved'.
    Once BIB is collected or race is finished the registration is locked.
    """
    from app.models.registration import Registration, RegistrationStatus
    result = await db.execute(
        select(Registration).where(
            Registration.event_id == event_id,
            Registration.user_id == current_user.id,
        )
    )
    reg = result.scalar_one_or_none()
    if reg is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registration not found")

    locked_statuses = {
        RegistrationStatus.bib_collected,
        RegistrationStatus.finished_certified,
    }
    if reg.status in locked_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel a registration with status '{reg.status.value}'",
        )

    await db.delete(reg)
    await db.commit()



@router.get("/me", response_model=StatusPageOut)
async def get_my_status(
    event_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StatusPageOut:
    """Participant views their registration status page for a specific event."""
    reg = await registration_service.get_registration_for_user(db, current_user.id, event_id)
    if reg is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registration not found for this event",
        )
    from app.services.registration_service import _build_status_page
    return _build_status_page(reg)


@router.post("/me/confirm", response_model=StatusPageOut)
async def confirm_participation(
    body: dict,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StatusPageOut:
    """Participant confirms participation (only valid when status=approved)."""
    event_id_raw = body.get("event_id")
    if not event_id_raw:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="event_id is required")

    try:
        event_id = uuid.UUID(str(event_id_raw))
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid event_id")

    # Find the registration
    reg = await registration_service.get_registration_for_user(db, current_user.id, event_id)
    if reg is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registration not found")

    updated = await registration_service.confirm_participation(db, reg.id, current_user.id)

    # Dispatch WhatsApp invite (stub in Sprint 2)
    phone = current_user.phone or "unknown"
    send_whatsapp_task.delay(
        to_phone=phone,
        message=f"Welcome to the marathon WhatsApp group! [link placeholder]",
        registration_id=str(updated.id),
    )

    from app.services.registration_service import _build_status_page
    return _build_status_page(updated)


@router.get("/{registration_id}/qr")
async def get_qr_url(
    registration_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Return a presigned URL for the registration's QR code image."""
    from sqlalchemy import select
    from app.models.registration import Registration
    result = await db.execute(
        select(Registration).where(Registration.id == registration_id)
    )
    reg = result.scalar_one_or_none()
    if reg is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registration not found")
    if reg.qr_code_url is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="QR code not yet generated")
    qr_url = storage_service.get_public_url(reg.qr_code_url)
    return {"qr_url": qr_url}
