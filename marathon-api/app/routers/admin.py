import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_role
from app.models.event import Event
from app.models.event_organizer import EventOrganizer
from app.models.organizer_invite import OrganizerInvite
from app.models.user import User
from app.schemas.admin import InviteCreateRequest, InviteOut, UserAdminOut
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])

_admin_only = Depends(require_role(["admin"]))


def _invite_status(invite: OrganizerInvite) -> str:
    if invite.accepted:
        return "accepted"
    if invite.expires_at < datetime.now(timezone.utc):
        return "expired"
    return "pending"


def _to_invite_out(invite: OrganizerInvite) -> InviteOut:
    return InviteOut(
        id=invite.id,
        email=invite.email,
        token=invite.token,
        invited_by=invite.invited_by,
        accepted=invite.accepted,
        expires_at=invite.expires_at,
        created_at=invite.created_at,
        status=_invite_status(invite),
    )


@router.post("/invites", response_model=InviteOut, status_code=status.HTTP_201_CREATED)
async def create_invite(
    body: InviteCreateRequest,
    current_user: Annotated[User, _admin_only],
    db: AsyncSession = Depends(get_db),
) -> InviteOut:
    # Check no existing user with this email
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, "User already exists with this email")

    # Check no pending non-expired invite
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(OrganizerInvite).where(
            OrganizerInvite.email == body.email,
            OrganizerInvite.accepted.is_(False),
            OrganizerInvite.expires_at > now,
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, "Pending invite already exists")

    invite = OrganizerInvite(
        email=body.email,
        token=uuid.uuid4(),
        invited_by=current_user.id,
        expires_at=now + timedelta(days=7),
    )
    db.add(invite)
    await db.commit()
    await db.refresh(invite)

    logger.info("[INVITE] Send invite to %s: /accept-invite?token=%s", body.email, invite.token)

    # Send the invite email — runs in a thread to avoid blocking the event loop.
    # Falls back to stub logging if SMTP_HOST is not configured.
    invite_url = f"{settings.FRONTEND_URL}/accept-invite?token={invite.token}"

    async def _send() -> None:
        from app.services.notification_service import send_email
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: send_email(
                to_email=body.email,
                subject="You've been invited to join as an organizer",
                body_html=(
                    f"<p>Hi,</p>"
                    f"<p>You have been invited to create an organizer account on the Marathon Management Platform.</p>"
                    f"<p><a href='{invite_url}' style='background:#4f46e5;color:#fff;padding:10px 20px;"
                    f"border-radius:6px;text-decoration:none;font-weight:600;display:inline-block;margin:12px 0'>"
                    f"Accept Invitation</a></p>"
                    f"<p>Or copy this link into your browser:<br>"
                    f"<code>{invite_url}</code></p>"
                    f"<p>This link expires on {invite.expires_at.strftime('%B %d, %Y')}.</p>"
                    f"<p>If you did not expect this invitation, you can ignore this email.</p>"
                ),
            ),
        )

    asyncio.create_task(_send())

    return _to_invite_out(invite)


@router.get("/invites", response_model=list[InviteOut])
async def list_invites(
    current_user: Annotated[User, _admin_only],
    db: AsyncSession = Depends(get_db),
) -> list[InviteOut]:
    result = await db.execute(select(OrganizerInvite).order_by(OrganizerInvite.created_at.desc()))
    return [_to_invite_out(inv) for inv in result.scalars().all()]


@router.get("/users")
async def list_users(
    current_user: Annotated[User, _admin_only],
    db: AsyncSession = Depends(get_db),
    role: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict[str, Any]:
    q = select(User)
    if role:
        q = q.where(User.role == role)
    total_result = await db.execute(select(func.count()).select_from(q.subquery()))
    total = total_result.scalar_one()
    result = await db.execute(q.offset((page - 1) * page_size).limit(page_size))
    items = [UserAdminOut.model_validate(u) for u in result.scalars().all()]
    return {"total": total, "page": page, "items": items}


@router.get("/events")
async def list_events_admin(
    current_user: Annotated[User, _admin_only],
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    events_result = await db.execute(select(Event))
    events = events_result.scalars().all()

    out = []
    for event in events:
        eo_result = await db.execute(
            select(User).join(EventOrganizer, User.id == EventOrganizer.user_id).where(
                EventOrganizer.event_id == event.id
            )
        )
        organizers = [{"id": str(u.id), "name": u.name, "email": u.email} for u in eo_result.scalars().all()]
        out.append(
            {
                "id": str(event.id),
                "name": event.name,
                "event_date": event.event_date.isoformat(),
                "location": event.location,
                "distances": event.distances,
                "sponsor_tiers": event.sponsor_tiers,
                "faq": event.faq,
                "is_active": event.is_active,
                "organizers": organizers,
            }
        )
    return out
