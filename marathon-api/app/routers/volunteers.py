import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.registration import Registration, RegistrationStatus
from app.models.user import User
from app.models.volunteer_assignment import VolunteerAssignment
from app.schemas.event import EventOut
from app.workers.tasks import send_email_task

router = APIRouter(prefix="/volunteers", tags=["volunteers"])

_volunteer_dep = Depends(require_role(["participant"]))


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ScanRequest(BaseModel):
    qr_code_data: str  # registration UUID string


class FinishRequest(BaseModel):
    qr_code_data: str  # registration UUID string
    finish_time: datetime | None = None  # defaults to now() if omitted


class ScanResult(BaseModel):
    success: bool
    participant_name: str
    bib_number: str
    status: str
    scanned_at: datetime


class VolunteerAssignmentOut(BaseModel):
    event: EventOut
    role_type: str
    category: str | None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_registration_and_check_assignment(
    db: AsyncSession,
    qr_code_data: str,
    user_id: uuid.UUID,
) -> tuple[Registration, VolunteerAssignment]:
    """Parse QR, fetch registration with lock, verify volunteer assignment."""
    try:
        registration_id = uuid.UUID(qr_code_data)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid QR code data — expected a registration UUID",
        )

    result = await db.execute(
        select(Registration)
        .options(selectinload(Registration.user))
        .where(Registration.id == registration_id)
        .with_for_update()
    )
    reg = result.scalar_one_or_none()
    if reg is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registration not found")

    assignment_result = await db.execute(
        select(VolunteerAssignment).where(
            VolunteerAssignment.user_id == user_id,
            VolunteerAssignment.event_id == reg.event_id,
        )
    )
    assignment = assignment_result.scalar_one_or_none()
    if assignment is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not assigned to this event",
        )

    return reg, assignment


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/scan", response_model=ScanResult)
async def scan_qr(
    body: ScanRequest,
    current_user: Annotated[User, _volunteer_dep],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ScanResult:
    """
    Registration-desk volunteer scans a participant's QR code.
    Transitions participation_confirmed → bib_collected.
    """
    reg, _ = await _get_registration_and_check_assignment(db, body.qr_code_data, current_user.id)

    if reg.status != RegistrationStatus.participation_confirmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot collect BIB — current status is '{reg.status.value}'. "
                f"Required: 'participation_confirmed'."
            ),
        )

    scanned_at = datetime.now(timezone.utc)
    reg.status = RegistrationStatus.bib_collected
    reg.bib_collected_at = scanned_at
    await db.commit()
    await db.refresh(reg)

    send_email_task.delay(
        to_email=reg.user.email,
        subject="Your BIB has been collected — see you at the start line!",
        body_html=(
            f"Hi {reg.user.name},<br><br>"
            f"Your BIB <strong>#{reg.bib_number}</strong> has been collected.<br>"
            f"See you at the start line!"
        ),
        registration_id=str(reg.id),
    )

    return ScanResult(
        success=True,
        participant_name=reg.user.name,
        bib_number=reg.bib_number or "N/A",
        status=reg.status.value,
        scanned_at=scanned_at,
    )


@router.post("/finish", response_model=ScanResult)
async def record_finish_time(
    body: FinishRequest,
    current_user: Annotated[User, _volunteer_dep],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ScanResult:
    """
    Finish-line volunteer scans a participant's QR and records their finish time.
    Transitions bib_collected → finished_certified and triggers certificate generation.
    finish_time defaults to now() if not provided.
    """
    reg, _ = await _get_registration_and_check_assignment(db, body.qr_code_data, current_user.id)

    if reg.status != RegistrationStatus.bib_collected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot record finish time — current status is '{reg.status.value}'. "
                f"Required: 'bib_collected'."
            ),
        )

    finish_time = body.finish_time or datetime.now(timezone.utc)
    reg.finish_time = finish_time
    reg.status = RegistrationStatus.finished_certified
    await db.commit()
    await db.refresh(reg)

    # Trigger async certificate generation
    from app.workers.tasks import generate_certificate_task
    generate_certificate_task.delay(str(reg.id))

    send_email_task.delay(
        to_email=reg.user.email,
        subject="🏅 You finished! Your certificate is being generated",
        body_html=(
            f"Hi {reg.user.name},<br><br>"
            f"Congratulations on finishing the race!<br>"
            f"Your finish time: <strong>{finish_time.strftime('%H:%M:%S')}</strong><br><br>"
            f"Your certificate will be emailed to you shortly."
        ),
        registration_id=str(reg.id),
    )

    return ScanResult(
        success=True,
        participant_name=reg.user.name,
        bib_number=reg.bib_number or "N/A",
        status=reg.status.value,
        scanned_at=finish_time,
    )


@router.get("/me/assignment", response_model=VolunteerAssignmentOut)
async def get_my_assignment(
    current_user: Annotated[User, _volunteer_dep],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> VolunteerAssignmentOut:
    """Return the volunteer's current event assignment."""
    result = await db.execute(
        select(VolunteerAssignment)
        .options(selectinload(VolunteerAssignment.event))
        .where(VolunteerAssignment.user_id == current_user.id)
        .order_by(VolunteerAssignment.created_at.desc())
        .limit(1)
    )
    assignment = result.scalar_one_or_none()

    if assignment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No volunteer assignment found",
        )

    return VolunteerAssignmentOut(
        event=EventOut.model_validate(assignment.event),
        role_type=assignment.role_type.value,
        category=assignment.category,
    )
