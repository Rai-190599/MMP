"""
Registration service — all business logic for the registration flow.

Status transition rules:
  registered → approved          (organizer assigns BIB)
  approved → participation_confirmed  (participant confirms)
  participation_confirmed → bib_collected  (volunteer scans — Sprint 3)
  bib_collected → finished_certified  (organizer enters finish time)
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.event import Event
from app.models.registration import Registration, RegistrationStatus
from app.schemas.registration import (
    RegistrationCreate,
    StageInfo,
    StatusPageOut,
)

# ---------------------------------------------------------------------------
# Stage mapping
# ---------------------------------------------------------------------------

_STATUS_TO_STAGE: dict[RegistrationStatus, int] = {
    RegistrationStatus.registered: 1,
    RegistrationStatus.approved: 2,
    RegistrationStatus.participation_confirmed: 3,
    RegistrationStatus.bib_collected: 4,
    RegistrationStatus.finished_certified: 5,
}

_STAGE_LABELS = [
    "Registered",
    "Approved & BIB Assigned",
    "Participation Confirmed",
    "BIB Collected",
    "Finished & Certified",
]


def _build_status_page(reg: Registration) -> StatusPageOut:
    """Convert a Registration ORM object into a StatusPageOut with the 5-stage tracker."""
    current = _STATUS_TO_STAGE[reg.status]

    # Timestamps per stage (where we have them)
    stage_timestamps: dict[int, Optional[datetime]] = {
        1: reg.created_at,
        2: None,   # no dedicated approved_at column — use bib assignment as proxy
        3: reg.confirmed_at,
        4: reg.bib_collected_at,
        5: reg.finish_time,
    }

    stages = [
        StageInfo(
            stage=i,
            label=_STAGE_LABELS[i - 1],
            completed=(i <= current),
            timestamp=stage_timestamps.get(i),
        )
        for i in range(1, 6)
    ]

    return StatusPageOut(
        id=reg.id,
        event_id=reg.event_id,
        user_id=reg.user_id,
        status=reg.status.value,
        distance=reg.distance,
        tshirt_size=reg.tshirt_size,
        emergency_contact=reg.emergency_contact,
        bib_number=reg.bib_number,
        qr_code_url=reg.qr_code_url,
        finish_time=reg.finish_time,
        certificate_url=reg.certificate_url,
        confirmed_at=reg.confirmed_at,
        bib_collected_at=reg.bib_collected_at,
        created_at=reg.created_at,
        current_stage=current,
        stages=stages,
    )


def _assert_transition(reg: Registration, required: RegistrationStatus, target: RegistrationStatus) -> None:
    """Raise 400 if the registration is not in the required status for a transition."""
    if reg.status != required:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot transition from '{reg.status.value}' to '{target.value}'. "
                f"Required current status: '{required.value}'."
            ),
        )


# ---------------------------------------------------------------------------
# Service functions
# ---------------------------------------------------------------------------

async def create_registration(
    db: AsyncSession,
    user_id: uuid.UUID,
    data: RegistrationCreate,
) -> Registration:
    """Create a new registration. Raises 409 if user is already registered for the event."""
    # Check for duplicate
    existing = await db.execute(
        select(Registration).where(
            Registration.event_id == data.event_id,
            Registration.user_id == user_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already registered for this event",
        )

    # Verify event exists
    event_result = await db.execute(select(Event).where(Event.id == data.event_id))
    if event_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event '{data.event_id}' not found",
        )

    reg = Registration(
        event_id=data.event_id,
        user_id=user_id,
        status=RegistrationStatus.registered,
        distance=data.distance,
        tshirt_size=data.tshirt_size,
        emergency_contact=data.emergency_contact,
    )
    db.add(reg)
    await db.commit()
    # Reload with user relationship for response serialisation
    await db.refresh(reg)
    result = await db.execute(
        select(Registration)
        .options(selectinload(Registration.user))
        .where(Registration.id == reg.id)
    )
    return result.scalar_one()


async def get_registration_for_user(
    db: AsyncSession,
    user_id: uuid.UUID,
    event_id: uuid.UUID,
) -> Optional[Registration]:
    """Return the registration for a specific user+event, or None."""
    result = await db.execute(
        select(Registration)
        .options(selectinload(Registration.user))
        .where(
            Registration.user_id == user_id,
            Registration.event_id == event_id,
        )
    )
    return result.scalar_one_or_none()


async def get_status_page(
    db: AsyncSession,
    registration_id: uuid.UUID,
) -> StatusPageOut:
    """Return the status page for a registration."""
    result = await db.execute(
        select(Registration).where(Registration.id == registration_id)
    )
    reg = result.scalar_one_or_none()
    if reg is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registration not found",
        )
    return _build_status_page(reg)


async def confirm_participation(
    db: AsyncSession,
    registration_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Registration:
    """Participant confirms participation. Only allowed when status=approved."""
    result = await db.execute(
        select(Registration)
        .options(selectinload(Registration.user))
        .where(Registration.id == registration_id)
    )
    reg = result.scalar_one_or_none()
    if reg is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registration not found")

    # Ownership check
    if reg.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your registration")

    _assert_transition(reg, RegistrationStatus.approved, RegistrationStatus.participation_confirmed)

    reg.status = RegistrationStatus.participation_confirmed
    reg.confirmed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(reg)
    return reg


async def assign_bib(
    db: AsyncSession,
    registration_id: uuid.UUID,
    bib_number: Optional[str],
) -> Registration:
    """
    Organizer approves a registration and assigns a BIB number.
    If bib_number is None, one is auto-generated as {EVENT_PREFIX}-{NNN}.
    Only allowed when status=registered.
    """
    result = await db.execute(
        select(Registration)
        .options(selectinload(Registration.user))
        .where(Registration.id == registration_id)
    )
    reg = result.scalar_one_or_none()
    if reg is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registration not found")

    _assert_transition(reg, RegistrationStatus.registered, RegistrationStatus.approved)

    # Auto-generate BIB if not provided
    if not bib_number:
        # Count existing approved+ registrations for this event to get sequence number
        count_result = await db.execute(
            select(func.count(Registration.id)).where(
                Registration.event_id == reg.event_id,
                Registration.status != RegistrationStatus.registered,
            )
        )
        seq = (count_result.scalar_one() or 0) + 1

        # Fetch event name for prefix (first 4 chars, uppercase, alphanumeric only)
        event_result = await db.execute(select(Event).where(Event.id == reg.event_id))
        event = event_result.scalar_one_or_none()
        prefix = ""
        if event:
            import re
            prefix = re.sub(r"[^A-Z0-9]", "", event.name.upper())[:4]
        if not prefix:
            prefix = "BIB"

        bib_number = f"{prefix}-{seq:03d}"

        # Ensure uniqueness — retry with higher seq if collision
        for _ in range(10):
            existing = await db.execute(
                select(Registration).where(Registration.bib_number == bib_number)
            )
            if existing.scalar_one_or_none() is None:
                break
            seq += 1
            bib_number = f"{prefix}-{seq:03d}"

    reg.bib_number = bib_number
    reg.status = RegistrationStatus.approved

    # Generate QR code and upload to MinIO (updates reg.qr_code_url in-place)
    try:
        from app.services.bib_service import generate_and_store_bib_qr
        await generate_and_store_bib_qr(db, reg)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).error("QR generation failed for %s: %s", registration_id, exc)
        # Non-fatal — BIB assignment still succeeds even if QR upload fails

    await db.commit()
    await db.refresh(reg)
    return reg


async def enter_finish_time(
    db: AsyncSession,
    registration_id: uuid.UUID,
    finish_time: datetime,
) -> Registration:
    """Organizer enters finish time. Only allowed when status=bib_collected."""
    result = await db.execute(
        select(Registration)
        .options(selectinload(Registration.user))
        .where(Registration.id == registration_id)
    )
    reg = result.scalar_one_or_none()
    if reg is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registration not found")

    _assert_transition(reg, RegistrationStatus.bib_collected, RegistrationStatus.finished_certified)

    reg.finish_time = finish_time
    reg.status = RegistrationStatus.finished_certified
    await db.commit()
    await db.refresh(reg)

    # Dispatch async certificate generation via Celery
    from app.workers.tasks import generate_certificate_task
    generate_certificate_task.delay(str(registration_id))

    return reg
