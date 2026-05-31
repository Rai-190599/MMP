import uuid
from datetime import date
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class EventCreate(BaseModel):
    name: str
    event_date: date
    location: Optional[str] = None
    distances: Optional[list[str]] = None
    sponsor_tiers: Optional[dict[str, Any]] = None
    faq: Optional[list[dict[str, Any]]] = None
    is_active: bool = True


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    event_date: date
    location: Optional[str] = None
    distances: Optional[list[str]] = None
    sponsor_tiers: Optional[dict[str, Any]] = None
    faq: Optional[list[dict[str, Any]]] = None
    is_active: bool
    banner_images: Optional[list[str]] = None  # public URLs, populated by router


class EventCreateRequest(BaseModel):
    name: str
    event_date: date
    location: str
    distances: list[str] = []
    sponsor_tiers: dict[str, Any] = {}
    faq: list[dict[str, Any]] = []


class EventUpdateRequest(BaseModel):
    name: Optional[str] = None
    event_date: Optional[date] = None
    location: Optional[str] = None
    distances: Optional[list[str]] = None
    sponsor_tiers: Optional[dict[str, Any]] = None
    faq: Optional[list[dict[str, Any]]] = None
    is_active: Optional[bool] = None
    volunteer_slot_caps: Optional[dict[str, int]] = None


# ---------------------------------------------------------------------------
# Browse / detail schemas (Change 3)
# ---------------------------------------------------------------------------

class EventListItem(BaseModel):
    """Lightweight summary used in the paginated event list."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    event_date: date
    location: Optional[str] = None
    distances: Optional[list[str]] = None
    is_active: bool
    # Computed fields — not ORM columns, populated manually in the router
    registration_count: int
    days_until_event: int


class EventListResponse(BaseModel):
    """Paginated wrapper returned by GET /events."""

    total: int
    page: int
    page_size: int
    items: list[EventListItem]


class EventDetail(EventOut):
    """
    Full event detail used by the event page.

    Extends EventOut with aggregate counts and the requesting user's
    own registration (None when unauthenticated or not registered).
    """

    # Import here to avoid circular dependency at module level;
    # the actual type is resolved at runtime via model_rebuild().
    registration_count: int
    registrations_by_status: dict[str, int]
    volunteer_slot_caps: Optional[dict[str, int]] = None
    volunteer_slots_filled: dict[str, int]
    is_registration_open: bool
    # Populated when the caller is authenticated and registered for this event
    user_registration: Optional[Any] = None  # RegistrationOut | None
    # Populated when the caller is authenticated and has a volunteer application
    user_volunteer_application: Optional[Any] = None  # VolunteerApplicationOut | None
