import csv
import io
import uuid
from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import require_role
from app.models.event_organizer import EventOrganizer
from app.models.registration import Registration, RegistrationStatus
from app.models.user import User
from app.models.volunteer_application import VolunteerApplication
from app.models.volunteer_assignment import VolunteerAssignment, VolunteerRoleType
from app.schemas.registration import BIBAssignRequest, FinishTimeRequest, RegistrationOut
from app.schemas.volunteer import VolunteerApplicationOut, VolunteerReviewRequest
from app.services import registration_service
from app.workers.tasks import send_email_task

router = APIRouter(prefix="/organizer", tags=["organizer"])

_organizer_dep = Depends(require_role(["organizer"]))


@router.get("/registrations", response_model=dict)
async def list_registrations(
    event_id: uuid.UUID,
    current_user: Annotated[User, _organizer_dep],
    db: Annotated[AsyncSession, Depends(get_db)],
    status_filter: Annotated[Optional[str], Query(alias="status")] = None,
    search: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    """
    List registrations for an event with optional status filter, name/email search,
    and pagination.
    """
    query = (
        select(Registration)
        .options(selectinload(Registration.user))
        .where(Registration.event_id == event_id)
    )

    if status_filter:
        try:
            s = RegistrationStatus(status_filter)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid status value: '{status_filter}'",
            )
        query = query.where(Registration.status == s)

    if search:
        # Join user for search — already eager-loaded, but we need it in WHERE
        query = query.join(Registration.user).where(
            or_(
                User.name.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
            )
        )

    # Count total before pagination
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    registrations = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "items": [RegistrationOut.model_validate(r) for r in registrations],
    }


@router.patch("/registrations/{registration_id}/approve", response_model=RegistrationOut)
async def approve_registration(
    registration_id: uuid.UUID,
    body: BIBAssignRequest,
    current_user: Annotated[User, _organizer_dep],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RegistrationOut:
    """Organizer approves a registration. BIB is auto-generated if not provided."""
    reg = await registration_service.assign_bib(db, registration_id, body.bib_number)

    # Build QR presigned URL for the email if QR was generated
    qr_html = ""
    if reg.qr_code_url:
        try:
            from app.services.storage_service import get_public_url
            qr_url = get_public_url(reg.qr_code_url)
            qr_html = (
                f"<p>Your QR code for race day check-in:</p>"
                f"<img src='{qr_url}' alt='QR Code' style='width:180px;height:180px;' />"
                f"<p><a href='{qr_url}'>Download QR code</a></p>"
            )
        except Exception:
            pass

    send_email_task.delay(
        to_email=reg.user.email,
        subject=f"You're approved! BIB #{reg.bib_number}",
        body_html=(
            f"Hi {reg.user.name},<br><br>"
            f"Great news — you've been approved!<br>"
            f"Your BIB number is: <strong>{reg.bib_number}</strong><br><br>"
            f"{qr_html}"
            f"Show this QR code at the registration desk on race day.<br><br>"
            f"See you at the race!"
        ),
        registration_id=str(reg.id),
    )

    return RegistrationOut.model_validate(reg)


@router.patch("/registrations/{registration_id}/finish-time", response_model=RegistrationOut)
async def set_finish_time(
    registration_id: uuid.UUID,
    body: FinishTimeRequest,
    current_user: Annotated[User, _organizer_dep],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RegistrationOut:
    """Organizer records a participant's finish time, transitioning to finished_certified."""
    reg = await registration_service.enter_finish_time(db, registration_id, body.finish_time)

    # Dispatch certificate-ready email (stub in Sprint 2)
    send_email_task.delay(
        to_email=reg.user.email,
        subject="Certificate ready — congratulations!",
        body_html=(
            f"Hi {reg.user.name},<br><br>"
            f"Congratulations on finishing the race!<br>"
            f"Your finish time: {reg.finish_time}<br>"
            f"Your certificate will be available for download soon. [placeholder]"
        ),
        registration_id=str(reg.id),
    )

    return RegistrationOut.model_validate(reg)


@router.post("/registrations/upload-finish-times", response_model=dict)
async def upload_finish_times(
    current_user: Annotated[User, _organizer_dep],
    db: Annotated[AsyncSession, Depends(get_db)],
    event_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
) -> dict:
    """
    Bulk-upload finish times from a CSV file.

    CSV format (header row required):
        bib_number,finish_time
        001,01:23:45
        002,2024-06-01T02:10:00

    finish_time accepts HH:MM:SS or ISO datetime.
    All valid rows are committed in a single transaction.
    Invalid/skipped rows are reported in the response without rolling back others.
    Max 1000 rows.
    """
    MAX_ROWS = 1000

    content = await file.read()
    try:
        text = content.decode("utf-8-sig")  # handle BOM
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="CSV file must be UTF-8 encoded")

    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None or not {"bib_number", "finish_time"}.issubset(
        {f.strip().lower() for f in reader.fieldnames}
    ):
        raise HTTPException(
            status_code=400,
            detail="CSV must have header row with columns: bib_number, finish_time",
        )

    rows = list(reader)
    if len(rows) > MAX_ROWS:
        raise HTTPException(
            status_code=400,
            detail=f"CSV exceeds {MAX_ROWS}-row limit. Found {len(rows)} rows.",
        )

    processed = 0
    skipped = 0
    warnings: list[str] = []
    errors: list[str] = []

    # Collect valid (registration, finish_time) pairs first, then commit once
    updates: list[tuple[Registration, datetime]] = []

    for i, row in enumerate(rows, start=2):  # row 1 = header
        bib = (row.get("bib_number") or "").strip()
        ft_raw = (row.get("finish_time") or "").strip()

        if not bib or not ft_raw:
            warnings.append(f"Row {i}: missing bib_number or finish_time — skipped")
            skipped += 1
            continue

        # Parse finish_time
        finish_time: Optional[datetime] = None
        for fmt in ("%H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                parsed = datetime.strptime(ft_raw, fmt)
                finish_time = parsed.replace(tzinfo=timezone.utc)
                break
            except ValueError:
                continue
        if finish_time is None:
            warnings.append(f"Row {i}: cannot parse finish_time '{ft_raw}' — skipped")
            skipped += 1
            continue

        # Find registration by bib_number + event_id
        result = await db.execute(
            select(Registration)
            .options(selectinload(Registration.user))
            .where(
                Registration.bib_number == bib,
                Registration.event_id == event_id,
            )
        )
        reg = result.scalar_one_or_none()

        if reg is None:
            warnings.append(f"Row {i}: BIB '{bib}' not found for this event — skipped")
            skipped += 1
            continue

        if reg.status != RegistrationStatus.bib_collected:
            warnings.append(
                f"Row {i}: BIB '{bib}' has status '{reg.status.value}' "
                f"(expected 'bib_collected') — skipped"
            )
            skipped += 1
            continue

        updates.append((reg, finish_time))

    # Apply all valid updates in one transaction
    if updates:
        try:
            for reg, finish_time in updates:
                reg.finish_time = finish_time
                reg.status = RegistrationStatus.finished_certified

            await db.commit()

            # Dispatch certificate tasks after successful commit
            from app.workers.tasks import generate_certificate_task
            for reg, _ in updates:
                generate_certificate_task.delay(str(reg.id))
                processed += 1

        except Exception as exc:
            await db.rollback()
            errors.append(f"Database error — all rows rolled back: {exc}")
            skipped += len(updates)

    return {
        "processed": processed,
        "skipped": skipped,
        "warnings": warnings,
        "errors": errors,
    }


@router.get("/registrations/summary", response_model=dict)
async def get_summary(
    event_id: uuid.UUID,
    current_user: Annotated[User, _organizer_dep],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Return counts per registration status for an event."""
    result = await db.execute(
        select(Registration.status, func.count(Registration.id))
        .where(Registration.event_id == event_id)
        .group_by(Registration.status)
    )
    rows = result.all()

    counts: dict[str, int] = {s.value: 0 for s in RegistrationStatus}
    for row_status, count in rows:
        counts[row_status.value] = count

    return {
        "registered": counts["registered"],
        "approved": counts["approved"],
        "participation_confirmed": counts["participation_confirmed"],
        "bib_collected": counts["bib_collected"],
        "finished_certified": counts["finished_certified"],
        "total": sum(counts.values()),
    }


# ---------------------------------------------------------------------------
# Volunteer application management (Change 4)
# ---------------------------------------------------------------------------

_DEFAULT_CAPS: dict[str, int] = {
    "registration_desk": 5,
    "finish_line": 3,
    "general": 10,
}


def _build_vol_app_out(
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


@router.get("/volunteer-applications", response_model=dict)
async def list_volunteer_applications(
    event_id: uuid.UUID,
    current_user: Annotated[User, _organizer_dep],
    db: Annotated[AsyncSession, Depends(get_db)],
    status_filter: Annotated[Optional[str], Query(alias="status")] = None,
) -> dict:
    """
    List volunteer applications for an event.
    Ordered oldest-first (FIFO) so organizers approve in submission order.
    """
    # Verify organizer owns this event
    eo_result = await db.execute(
        select(EventOrganizer).where(
            EventOrganizer.event_id == event_id,
            EventOrganizer.user_id == current_user.id,
        )
    )
    if eo_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized for this event",
        )

    query = (
        select(VolunteerApplication)
        .where(VolunteerApplication.event_id == event_id)
        .order_by(VolunteerApplication.applied_at.asc())
    )
    if status_filter:
        if status_filter not in ("pending", "approved", "rejected"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid status filter: '{status_filter}'",
            )
        query = query.where(VolunteerApplication.status == status_filter)

    result = await db.execute(query)
    applications = result.scalars().all()

    # Fetch event for slot caps
    from app.models.event import Event
    event_result = await db.execute(select(Event).where(Event.id == event_id))
    event = event_result.scalar_one_or_none()
    caps: dict[str, int] = (event.volunteer_slot_caps if event else None) or _DEFAULT_CAPS

    # Count approved per role in one query
    filled_result = await db.execute(
        select(VolunteerApplication.desired_role, func.count().label("cnt"))
        .where(
            VolunteerApplication.event_id == event_id,
            VolunteerApplication.status == "approved",
        )
        .group_by(VolunteerApplication.desired_role)
    )
    filled_by_role: dict[str, int] = {row.desired_role: row.cnt for row in filled_result}

    items: list[VolunteerApplicationOut] = []
    for app in applications:
        user_result = await db.execute(select(User).where(User.id == app.user_id))
        user = user_result.scalar_one_or_none()
        if user is None:
            continue
        cap = caps.get(app.desired_role, 0)
        filled = filled_by_role.get(app.desired_role, 0)
        items.append(_build_vol_app_out(app, user, max(cap - filled, 0)))

    return {"total": len(items), "items": [i.model_dump() for i in items]}


@router.patch(
    "/volunteer-applications/{application_id}",
    response_model=VolunteerApplicationOut,
)
async def review_volunteer_application(
    application_id: uuid.UUID,
    body: VolunteerReviewRequest,
    current_user: Annotated[User, _organizer_dep],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> VolunteerApplicationOut:
    """
    Organizer approves or rejects a volunteer application.

    On approval:
    - Re-checks slot cap to handle race conditions (two organizers approving simultaneously).
    - Creates a volunteer_assignments row.
    - Dispatches approval email notification.

    On rejection:
    - Sets status to rejected and dispatches rejection email.
    """
    # Fetch application
    app_result = await db.execute(
        select(VolunteerApplication).where(VolunteerApplication.id == application_id)
    )
    application = app_result.scalar_one_or_none()
    if application is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Volunteer application not found",
        )

    # Verify organizer owns the event
    eo_result = await db.execute(
        select(EventOrganizer).where(
            EventOrganizer.event_id == application.event_id,
            EventOrganizer.user_id == current_user.id,
        )
    )
    if eo_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized for this event",
        )

    if application.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Application is already '{application.status}' and cannot be reviewed again",
        )

    # Fetch applicant user
    user_result = await db.execute(select(User).where(User.id == application.user_id))
    applicant = user_result.scalar_one_or_none()
    if applicant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Applicant user not found")

    now = datetime.now(timezone.utc)

    if body.status == "approved":
        # Re-check slot cap — race condition safety
        from app.models.event import Event
        event_result = await db.execute(
            select(Event).where(Event.id == application.event_id)
        )
        event = event_result.scalar_one_or_none()
        caps: dict[str, int] = (event.volunteer_slot_caps if event else None) or _DEFAULT_CAPS
        cap = caps.get(application.desired_role, 0)

        filled_result = await db.execute(
            select(func.count())
            .select_from(VolunteerApplication)
            .where(
                VolunteerApplication.event_id == application.event_id,
                VolunteerApplication.desired_role == application.desired_role,
                VolunteerApplication.status == "approved",
            )
        )
        filled = filled_result.scalar_one()

        if filled >= cap:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Cannot approve: all {cap} slot(s) for '{application.desired_role}' "
                    "have already been filled"
                ),
            )

        # Approve application
        application.status = "approved"
        application.reviewed_at = now

        # Create volunteer_assignments row
        try:
            role_type = VolunteerRoleType(application.desired_role)
        except ValueError:
            role_type = VolunteerRoleType.general

        assignment = VolunteerAssignment(
            event_id=application.event_id,
            user_id=application.user_id,
            role_type=role_type,
            category=application.desired_role,
        )
        db.add(assignment)
        await db.commit()
        await db.refresh(application)

        # Dispatch approval email
        send_email_task.delay(
            to_email=applicant.email,
            subject=f"Your volunteer application for {application.desired_role} has been approved",
            body_html=(
                f"Hi {applicant.name},<br><br>"
                f"Great news — your volunteer application for the role "
                f"<strong>{application.desired_role}</strong> has been approved.<br><br>"
                f"See you at the event!"
            ),
            registration_id=None,
        )

        slots_remaining = max(cap - filled - 1, 0)

    else:  # rejected
        application.status = "rejected"
        application.reviewed_at = now
        await db.commit()
        await db.refresh(application)

        # Dispatch rejection email
        send_email_task.delay(
            to_email=applicant.email,
            subject="Update on your volunteer application",
            body_html=(
                f"Hi {applicant.name},<br><br>"
                f"Thank you for your interest in volunteering. "
                f"Unfortunately, your application was not approved this time.<br><br>"
                f"We hope to see you at the event as a participant!"
            ),
            registration_id=None,
        )

        # Slots remaining unchanged for rejections — recompute
        from app.models.event import Event
        event_result = await db.execute(
            select(Event).where(Event.id == application.event_id)
        )
        event = event_result.scalar_one_or_none()
        caps = (event.volunteer_slot_caps if event else None) or _DEFAULT_CAPS
        cap = caps.get(application.desired_role, 0)
        filled_result = await db.execute(
            select(func.count())
            .select_from(VolunteerApplication)
            .where(
                VolunteerApplication.event_id == application.event_id,
                VolunteerApplication.desired_role == application.desired_role,
                VolunteerApplication.status == "approved",
            )
        )
        filled = filled_result.scalar_one()
        slots_remaining = max(cap - filled, 0)

    return _build_vol_app_out(application, applicant, slots_remaining)
