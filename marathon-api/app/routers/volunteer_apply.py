import logging
import uuid
from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.event import Event
from app.models.user import User
from app.models.volunteer_application import VolunteerApplication
from app.schemas.volunteer import (
    VolunteerApplyRequest,
    VolunteerApplicationOut,
    VolunteerSlotsOut,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/volunteer-applications", tags=["volunteer-applications"])

_participant_dep = Depends(require_role(["participant"]))

# Default slot caps used when event.volunteer_slot_caps is NULL
_DEFAULT_CAPS: dict[str, int] = {
    "registration_desk": 5,
    "finish_line": 3,
    "general": 10,
}


def _build_application_out(
    app: VolunteerApplication,
    user: User,
    slots_remaining: int,
) -> VolunteerApplicationOut:
    return VolunteerApplicationOut(
        id=app.id,
        event_id=app.event_id,
        user_id=app.user_id,
        desired_role=app.desired_role,
        status=app.status,
        note=app.note,
        applied_at=app.applied_at,
        reviewed_at=app.reviewed_at,
        user_name=user.name,
        user_email=user.email,
        slots_remaining=slots_remaining,
    )


async def _count_approved(
    db: AsyncSession, event_id: uuid.UUID, desired_role: str
) -> int:
    """Count approved volunteer applications for a given role on an event."""
    result = await db.execute(
        select(func.count())
        .select_from(VolunteerApplication)
        .where(
            VolunteerApplication.event_id == event_id,
            VolunteerApplication.desired_role == desired_role,
            VolunteerApplication.status == "approved",
        )
    )
    return result.scalar_one()


async def _get_cap(event: Event, desired_role: str) -> int:
    caps: dict[str, int] = event.volunteer_slot_caps or _DEFAULT_CAPS
    return caps.get(desired_role, 0)


# ---------------------------------------------------------------------------
# POST /volunteer-applications  — participant applies
# ---------------------------------------------------------------------------

@router.post("/", response_model=VolunteerApplicationOut, status_code=status.HTTP_201_CREATED)
async def apply_to_volunteer(
    body: VolunteerApplyRequest,
    current_user: Annotated[User, _participant_dep],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> VolunteerApplicationOut:
    """
    Any authenticated participant can apply to volunteer for a specific role on an event.
    They do not need to be a registered participant — volunteering is a separate role.
    """
    # 1. Check no existing application for this event by this user
    existing_result = await db.execute(
        select(VolunteerApplication).where(
            VolunteerApplication.event_id == body.event_id,
            VolunteerApplication.user_id == current_user.id,
        )
    )
    if existing_result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have a volunteer application for this event",
        )

    # 2. Fetch event and check it exists
    event_result = await db.execute(select(Event).where(Event.id == body.event_id))
    event = event_result.scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    cap = await _get_cap(event, body.desired_role)
    filled = await _count_approved(db, body.event_id, body.desired_role)

    # 3. Slot cap check
    if filled >= cap:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No slots available for {body.desired_role} role",
        )

    # 4. Create application
    application = VolunteerApplication(
        event_id=body.event_id,
        user_id=current_user.id,
        desired_role=body.desired_role,
        status="pending",
        note=body.note,
    )
    db.add(application)
    await db.commit()
    await db.refresh(application)

    logger.info(
        "[NOTIFY] Organizer notified of new volunteer application: user=%s event=%s role=%s",
        current_user.email,
        body.event_id,
        body.desired_role,
    )

    slots_remaining = cap - filled - 1
    return _build_application_out(application, current_user, max(slots_remaining, 0))


# ---------------------------------------------------------------------------
# GET /volunteer-applications/me  — participant views own applications
# ---------------------------------------------------------------------------

@router.get("/me", response_model=list[VolunteerApplicationOut])
async def get_my_applications(
    current_user: Annotated[User, _participant_dep],
    db: Annotated[AsyncSession, Depends(get_db)],
    event_id: Optional[uuid.UUID] = Query(default=None),
) -> list[VolunteerApplicationOut]:
    """Return the authenticated participant's volunteer applications."""
    query = select(VolunteerApplication).where(
        VolunteerApplication.user_id == current_user.id
    )
    if event_id is not None:
        query = query.where(VolunteerApplication.event_id == event_id)

    result = await db.execute(query)
    applications = result.scalars().all()

    items: list[VolunteerApplicationOut] = []
    for app in applications:
        event_result = await db.execute(select(Event).where(Event.id == app.event_id))
        event = event_result.scalar_one_or_none()
        cap = await _get_cap(event, app.desired_role) if event else 0
        filled = await _count_approved(db, app.event_id, app.desired_role)
        items.append(
            _build_application_out(app, current_user, max(cap - filled, 0))
        )

    return items


# ---------------------------------------------------------------------------
# DELETE /volunteer-applications/{application_id}  — participant withdraws
# ---------------------------------------------------------------------------

@router.delete("/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
async def withdraw_application(
    application_id: uuid.UUID,
    current_user: Annotated[User, _participant_dep],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """
    Participant withdraws a pending volunteer application.
    Returns 400 if the application has already been approved.
    """
    result = await db.execute(
        select(VolunteerApplication).where(
            VolunteerApplication.id == application_id,
            VolunteerApplication.user_id == current_user.id,
        )
    )
    application = result.scalar_one_or_none()
    if application is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Volunteer application not found",
        )
    if application.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot withdraw an application that is not pending",
        )

    await db.delete(application)
    await db.commit()


# ---------------------------------------------------------------------------
# GET /volunteer-applications/event/{event_id}/slots  — public slot counts
# ---------------------------------------------------------------------------

@router.get(
    "/event/{event_id}/slots",
    response_model=VolunteerSlotsOut,
    status_code=status.HTTP_200_OK,
)
async def get_event_slots(
    event_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> VolunteerSlotsOut:
    """
    Public — returns cap, filled, and remaining volunteer slots per role for an event.
    Used by the frontend to show "2 slots left" on the volunteer apply button.
    """
    event_result = await db.execute(select(Event).where(Event.id == event_id))
    event = event_result.scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    caps: dict[str, int] = event.volunteer_slot_caps or _DEFAULT_CAPS

    # Count all approved applications per role in one query
    filled_result = await db.execute(
        select(VolunteerApplication.desired_role, func.count().label("cnt"))
        .where(
            VolunteerApplication.event_id == event_id,
            VolunteerApplication.status == "approved",
        )
        .group_by(VolunteerApplication.desired_role)
    )
    filled_by_role: dict[str, int] = {row.desired_role: row.cnt for row in filled_result}

    from app.schemas.volunteer import _SlotInfo  # local import to avoid re-export noise

    slots = [
        _SlotInfo(
            role=role,
            cap=cap,
            filled=filled_by_role.get(role, 0),
            remaining=max(cap - filled_by_role.get(role, 0), 0),
            is_open=(cap - filled_by_role.get(role, 0)) > 0,
        )
        for role, cap in caps.items()
    ]

    return VolunteerSlotsOut(event_id=event_id, slots=slots)
