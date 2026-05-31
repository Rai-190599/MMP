import uuid
from datetime import date, datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.event import Event
from app.models.registration import Registration, RegistrationStatus
from app.models.user import User
from app.models.volunteer_application import VolunteerApplication
from app.schemas.event import EventDetail, EventListItem, EventListResponse, EventOut
from app.schemas.registration import RegistrationOut
from app.services.storage_service import get_public_url

router = APIRouter(prefix="/events", tags=["events"])

# Optional bearer — does NOT raise 401 when token is absent
_optional_bearer = HTTPBearer(auto_error=False)


async def _get_optional_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_optional_bearer)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Optional[User]:
    """
    Decode JWT if present and return the User; return None if no token or
    token is invalid.  Never raises 401 — callers handle the None case.
    """
    if credentials is None:
        return None
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        user_id_str: str | None = payload.get("sub")
        if user_id_str is None:
            return None
        user_id = uuid.UUID(user_id_str)
    except (JWTError, ValueError):
        return None

    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


def _days_until(event_date: date) -> int:
    """Positive = future, negative = past, 0 = today."""
    return (event_date - datetime.now(timezone.utc).date()).days


def _event_to_out(event: Event) -> EventOut:
    """Convert Event ORM object to EventOut, resolving banner object names to public URLs."""
    from app.services.storage_service import get_public_url
    banner_urls = [get_public_url(obj) for obj in (event.banner_images or [])]
    return EventOut(
        id=event.id,
        name=event.name,
        event_date=event.event_date,
        location=event.location,
        distances=event.distances,
        sponsor_tiers=event.sponsor_tiers,
        faq=event.faq,
        is_active=event.is_active,
        banner_images=banner_urls if banner_urls else None,
    )


# ---------------------------------------------------------------------------
# Existing endpoint — unchanged
# ---------------------------------------------------------------------------

@router.get("/{event_id}", response_model=EventOut, status_code=status.HTTP_200_OK)
async def get_event(
    event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> EventOut:
    """Public endpoint — returns full event details by ID."""
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()

    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with id '{event_id}' not found",
        )

    return _event_to_out(event)


# ---------------------------------------------------------------------------
# New endpoints (Change 3)
# ---------------------------------------------------------------------------

@router.get("", response_model=EventListResponse, status_code=status.HTTP_200_OK)
async def list_events(
    db: Annotated[AsyncSession, Depends(get_db)],
    is_active: bool = Query(default=True, description="Filter by active status"),
    upcoming: bool = Query(
        default=True, description="Only return events where event_date >= today"
    ),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=10, ge=1, le=50, description="Items per page (max 50)"),
) -> EventListResponse:
    """
    Public — paginated list of events.

    registration_count reflects only approved+ registrations (status != 'registered')
    so it represents real confirmed participation numbers.
    """
    today = datetime.now(timezone.utc).date()

    # Base filter
    filters = [Event.is_active == is_active]
    if upcoming:
        filters.append(Event.event_date >= today)

    # Total count
    count_result = await db.execute(
        select(func.count()).select_from(Event).where(*filters)
    )
    total = count_result.scalar_one()

    # Fetch page of events ordered soonest-first
    offset = (page - 1) * page_size
    events_result = await db.execute(
        select(Event)
        .where(*filters)
        .order_by(Event.event_date.asc())
        .offset(offset)
        .limit(page_size)
    )
    events = events_result.scalars().all()

    if not events:
        return EventListResponse(total=total, page=page, page_size=page_size, items=[])

    event_ids = [e.id for e in events]

    # Count approved+ registrations per event in one query
    reg_counts_result = await db.execute(
        select(Registration.event_id, func.count().label("cnt"))
        .where(
            Registration.event_id.in_(event_ids),
            Registration.status != RegistrationStatus.registered,
        )
        .group_by(Registration.event_id)
    )
    reg_counts: dict[uuid.UUID, int] = {
        row.event_id: row.cnt for row in reg_counts_result
    }

    items = [
        EventListItem(
            id=e.id,
            name=e.name,
            event_date=e.event_date,
            location=e.location,
            distances=e.distances,
            is_active=e.is_active,
            registration_count=reg_counts.get(e.id, 0),
            days_until_event=_days_until(e.event_date),
        )
        for e in events
    ]

    return EventListResponse(total=total, page=page, page_size=page_size, items=items)


@router.get("/{event_id}/detail", response_model=EventDetail, status_code=status.HTTP_200_OK)
async def get_event_detail(
    event_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Optional[User], Depends(_get_optional_user)],
) -> EventDetail:
    """
    Public — full event detail with aggregate counts.
    Optional auth: if a valid JWT is provided, user_registration is populated.
    No 401 is raised when the token is absent or invalid.
    """
    # Fetch event
    event_result = await db.execute(select(Event).where(Event.id == event_id))
    event = event_result.scalar_one_or_none()
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with id '{event_id}' not found",
        )

    today = datetime.now(timezone.utc).date()

    # Registrations grouped by status
    reg_by_status_result = await db.execute(
        select(Registration.status, func.count().label("cnt"))
        .where(Registration.event_id == event_id)
        .group_by(Registration.status)
    )
    registrations_by_status: dict[str, int] = {
        row.status.value: row.cnt for row in reg_by_status_result
    }

    # registration_count = approved+ only (excludes bare 'registered')
    registration_count = sum(
        cnt
        for status_val, cnt in registrations_by_status.items()
        if status_val != RegistrationStatus.registered.value
    )

    # Volunteer slots filled — count approved volunteer_applications per desired_role
    slots_filled_result = await db.execute(
        select(
            VolunteerApplication.desired_role,
            func.count().label("cnt"),
        )
        .where(
            VolunteerApplication.event_id == event_id,
            VolunteerApplication.status == "approved",
        )
        .group_by(VolunteerApplication.desired_role)
    )
    volunteer_slots_filled: dict[str, int] = {
        row.desired_role: row.cnt for row in slots_filled_result
    }

    # Slot caps from the event (default if column is NULL)
    default_caps: dict[str, int] = {
        "registration_desk": 5,
        "finish_line": 3,
        "general": 10,
    }
    slot_caps: dict[str, int] = event.volunteer_slot_caps or default_caps

    is_registration_open = bool(event.is_active and event.event_date > today)

    # User's own registration (None if unauthenticated or not registered)
    user_registration = None
    user_volunteer_application = None
    if current_user is not None:
        reg_result = await db.execute(
            select(Registration).where(
                Registration.event_id == event_id,
                Registration.user_id == current_user.id,
            )
        )
        reg = reg_result.scalar_one_or_none()
        if reg is not None:
            user_registration = RegistrationOut.model_validate(reg)

        # Fetch volunteer application for this user+event
        vol_result = await db.execute(
            select(VolunteerApplication).where(
                VolunteerApplication.event_id == event_id,
                VolunteerApplication.user_id == current_user.id,
            )
        )
        vol_app = vol_result.scalar_one_or_none()
        if vol_app is not None:
            user_volunteer_application = {
                "id": str(vol_app.id),
                "desired_role": vol_app.desired_role,
                "status": vol_app.status,
                "applied_at": vol_app.applied_at.isoformat() if vol_app.applied_at else None,
            }

    return EventDetail(
        id=event.id,
        name=event.name,
        event_date=event.event_date,
        location=event.location,
        distances=event.distances,
        sponsor_tiers=event.sponsor_tiers,
        faq=event.faq,
        is_active=event.is_active,
        banner_images=[get_public_url(obj) for obj in (event.banner_images or [])] or None,
        registration_count=registration_count,
        registrations_by_status=registrations_by_status,
        volunteer_slot_caps=slot_caps,
        volunteer_slots_filled=volunteer_slots_filled,
        is_registration_open=is_registration_open,
        user_registration=user_registration,
        user_volunteer_application=user_volunteer_application,
    )
