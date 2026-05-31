import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_role
from app.models.event import Event
from app.models.event_organizer import EventOrganizer
from app.models.user import User
from app.schemas.event import EventCreateRequest, EventOut, EventUpdateRequest

router = APIRouter(prefix="/manage/events", tags=["event-management"])

_org_or_admin = Depends(require_role(["organizer", "admin"]))


@router.post("/", response_model=EventOut, status_code=status.HTTP_201_CREATED)
async def create_event(
    body: EventCreateRequest,
    current_user: Annotated[User, _org_or_admin],
    db: AsyncSession = Depends(get_db),
) -> EventOut:
    event = Event(
        name=body.name,
        event_date=body.event_date,
        location=body.location,
        distances=body.distances,
        sponsor_tiers=body.sponsor_tiers,
        faq=body.faq,
    )
    db.add(event)
    await db.flush()

    if current_user.role.value != "admin":
        db.add(EventOrganizer(event_id=event.id, user_id=current_user.id))

    await db.commit()
    await db.refresh(event)
    return EventOut.model_validate(event)


@router.get("/", response_model=list[EventOut])
async def list_events(
    current_user: Annotated[User, _org_or_admin],
    db: AsyncSession = Depends(get_db),
) -> list[EventOut]:
    if current_user.role.value == "admin":
        result = await db.execute(select(Event))
    else:
        result = await db.execute(
            select(Event)
            .join(EventOrganizer, Event.id == EventOrganizer.event_id)
            .where(EventOrganizer.user_id == current_user.id)
        )
    return [EventOut.model_validate(e) for e in result.scalars().all()]


@router.patch("/{event_id}", response_model=EventOut)
async def update_event(
    event_id: uuid.UUID,
    body: EventUpdateRequest,
    current_user: Annotated[User, _org_or_admin],
    db: AsyncSession = Depends(get_db),
) -> EventOut:
    if current_user.role.value == "organizer":
        eo = await db.execute(
            select(EventOrganizer).where(
                EventOrganizer.event_id == event_id,
                EventOrganizer.user_id == current_user.id,
            )
        )
        if not eo.scalar_one_or_none():
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized to edit this event")

    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Event not found")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(event, field, value)

    await db.commit()
    await db.refresh(event)
    return EventOut.model_validate(event)


@router.post("/{event_id}/co-organizer", status_code=status.HTTP_201_CREATED)
async def add_co_organizer(
    event_id: uuid.UUID,
    body: dict[str, Any],
    current_user: Annotated[User, _org_or_admin],
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    target_user_id = uuid.UUID(str(body.get("user_id")))

    # Auth check: must own event or be admin
    if current_user.role.value != "admin":
        eo = await db.execute(
            select(EventOrganizer).where(
                EventOrganizer.event_id == event_id,
                EventOrganizer.user_id == current_user.id,
            )
        )
        if not eo.scalar_one_or_none():
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized for this event")

    # Validate target user is an organizer
    user_result = await db.execute(select(User).where(User.id == target_user_id))
    target = user_result.scalar_one_or_none()
    if not target or target.role.value != "organizer":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Target user must have role=organizer")

    # Check not already assigned
    existing = await db.execute(
        select(EventOrganizer).where(
            EventOrganizer.event_id == event_id,
            EventOrganizer.user_id == target_user_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, "User is already a co-organizer")

    db.add(EventOrganizer(event_id=event_id, user_id=target_user_id))
    await db.commit()
    return {"message": "Co-organizer added"}


@router.post("/{event_id}/banners", status_code=status.HTTP_201_CREATED)
async def upload_banner(
    event_id: uuid.UUID,
    current_user: Annotated[User, _org_or_admin],
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Upload a banner image for an event.
    Accepts JPEG or PNG. Stored in MinIO under banners/{event_id}/{filename}.
    Returns the public URL of the uploaded image.
    Max 5 banners per event.
    """
    # Auth check
    if current_user.role.value == "organizer":
        eo = await db.execute(
            select(EventOrganizer).where(
                EventOrganizer.event_id == event_id,
                EventOrganizer.user_id == current_user.id,
            )
        )
        if not eo.scalar_one_or_none():
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized for this event")

    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Event not found")

    # Validate content type
    content_type = file.content_type or ""
    if content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Only JPEG, PNG, and WebP images are accepted",
        )

    current_banners: list = event.banner_images or []
    if len(current_banners) >= 5:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Maximum 5 banner images per event",
        )

    # Read and upload
    file_bytes = await file.read()
    ext = "jpg" if "jpeg" in content_type else content_type.split("/")[-1]
    object_name = f"banners/{event_id}/{len(current_banners) + 1}.{ext}"

    from app.services.storage_service import upload_file, get_public_url
    upload_file(file_bytes=file_bytes, object_name=object_name, content_type=content_type)

    # Make banners prefix public (idempotent)
    try:
        import subprocess
        subprocess.run(
            ["mc", "anonymous", "set", "public", f"local/marathon-files/banners"],
            capture_output=True, timeout=5,
        )
    except Exception:
        pass  # mc may not be available outside MinIO container — handled separately

    # Persist object_name in event
    updated_banners = current_banners + [object_name]
    event.banner_images = updated_banners
    await db.commit()

    public_url = get_public_url(object_name)
    return {"object_name": object_name, "url": public_url, "banner_images": updated_banners}


@router.delete("/{event_id}/banners/{index}", status_code=status.HTTP_200_OK)
async def delete_banner(
    event_id: uuid.UUID,
    index: int,
    current_user: Annotated[User, _org_or_admin],
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Remove a banner image by its 0-based index."""
    if current_user.role.value == "organizer":
        eo = await db.execute(
            select(EventOrganizer).where(
                EventOrganizer.event_id == event_id,
                EventOrganizer.user_id == current_user.id,
            )
        )
        if not eo.scalar_one_or_none():
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized for this event")

    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Event not found")

    banners = list(event.banner_images or [])
    if index < 0 or index >= len(banners):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Banner index out of range")

    banners.pop(index)
    event.banner_images = banners
    await db.commit()
    return {"banner_images": banners}
