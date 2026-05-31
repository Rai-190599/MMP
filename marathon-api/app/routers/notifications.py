"""
Notification router — broadcast and history endpoints.
All routes require organizer role.
"""
import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import require_role
from app.models.notification import Notification
from app.models.registration import Registration
from app.models.user import User
from app.schemas.notification import BroadcastRequest, NotificationLogOut

router = APIRouter(prefix="/notifications", tags=["notifications"])

_organizer_dep = Depends(require_role(["organizer"]))

BROADCAST_RECIPIENT_CAP = 500


@router.post("/broadcast", status_code=status.HTTP_200_OK)
async def broadcast(
    body: BroadcastRequest,
    current_user: Annotated[User, _organizer_dep],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """
    Queue a notification broadcast to all (or filtered) registrations for an event.
    Capped at 500 recipients.
    """
    query = select(Registration).where(Registration.event_id == body.event_id)
    if body.filter_status is not None:
        query = query.where(Registration.status == body.filter_status)

    result = await db.execute(query)
    registrations = result.scalars().all()

    if len(registrations) > BROADCAST_RECIPIENT_CAP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Broadcast exceeds the {BROADCAST_RECIPIENT_CAP}-recipient cap. "
                f"Found {len(registrations)} recipients. Use filter_status to narrow the audience."
            ),
        )

    from app.workers.tasks import send_broadcast_task

    for reg in registrations:
        send_broadcast_task.delay(
            registration_id=str(reg.id),
            channel=body.channel.value,
            subject=body.subject,
            message=body.message,
        )

    return {
        "queued": len(registrations),
        "message": f"Broadcast queued for {len(registrations)} recipients",
    }


@router.get("/history", response_model=dict)
async def notification_history(
    event_id: uuid.UUID,
    current_user: Annotated[User, _organizer_dep],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    channel: Optional[str] = None,
) -> dict:
    """
    Return paginated notification history for an event, with recipient info.
    """
    # Base query — join through Registration → User
    query = (
        select(Notification)
        .join(Notification.registration)
        .options(
            selectinload(Notification.registration).selectinload(Registration.user)
        )
        .where(Registration.event_id == event_id)
        .order_by(Notification.created_at.desc())
    )

    if channel:
        from app.models.notification import NotificationChannel
        try:
            ch = NotificationChannel(channel)
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid channel: '{channel}'")
        query = query.where(Notification.channel == ch)

    # Count
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar_one()

    # Paginate
    offset = (page - 1) * page_size
    result = await db.execute(query.offset(offset).limit(page_size))
    notifications = result.scalars().all()

    items = []
    for n in notifications:
        user = n.registration.user if n.registration else None
        items.append(
            NotificationLogOut(
                id=n.id,
                registration_id=n.registration_id,
                channel=n.channel.value,
                trigger_type=n.trigger_type.value,
                content=n.content,
                sent=n.sent,
                sent_at=n.sent_at,
                created_at=n.created_at,
                recipient_name=user.name if user else None,
                recipient_email=user.email if user else None,
            )
        )

    return {"total": total, "page": page, "items": [i.model_dump() for i in items]}
