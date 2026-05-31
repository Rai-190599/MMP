import logging
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.organizer_invite import OrganizerInvite
from app.models.registration import Registration, RegistrationStatus
from app.models.user import User, UserRole
from app.schemas.admin import AcceptInviteRequest
from app.schemas.auth import LoginRequest, RegisterRequest, SignupRequest, SignupResponse, TokenResponse, UserOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _hash_password(password: str) -> str:
    return pwd_context.hash(password)


def _verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _create_access_token(user_id: uuid.UUID, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.ACCESS_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


@router.post("/signup", response_model=SignupResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    body: SignupRequest,
    db: AsyncSession = Depends(get_db),
) -> SignupResponse:
    """Create a participant account without registering for an event."""
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already in use",
        )

    user = User(
        name=body.name,
        email=body.email,
        phone=body.phone,
        role=UserRole.participant,
        password_hash=_hash_password(body.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    logger.info("[EMAIL] Welcome email to %s", body.email)

    token = _create_access_token(user.id, UserRole.participant.value)
    return SignupResponse(
        access_token=token,
        token_type="bearer",
        user=UserOut.model_validate(user),
    )


# DEPRECATED — use POST /auth/signup instead
@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Register a new participant or volunteer user."""
    # Check for duplicate email
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Email '{body.email}' is already registered",
        )

    # Create user
    user = User(
        name=body.name,
        email=body.email,
        phone=body.phone,
        role=UserRole(body.role),
        password_hash=_hash_password(body.password),
    )
    db.add(user)
    await db.flush()  # Flush to get user.id before creating registration

    # If participant with event_id, create registration
    if body.role == "participant" and body.event_id is not None:
        registration = Registration(
            event_id=body.event_id,
            user_id=user.id,
            status=RegistrationStatus.registered,
            distance=body.distance,
            tshirt_size=body.tshirt_size,
            emergency_contact=body.emergency_contact,
        )
        db.add(registration)

    await db.commit()
    await db.refresh(user)

    # Stub notification — real email in Sprint 2
    logger.info("would send welcome email to %s", body.email)

    token = _create_access_token(user.id, user.role.value)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserOut.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate a user and return a JWT token."""
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if user is None or not _verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = _create_access_token(user.id, user.role.value)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserOut.model_validate(user),
    )


@router.post("/accept-invite", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def accept_invite(
    body: AcceptInviteRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Accept an organizer invite and create an organizer account."""
    result = await db.execute(select(OrganizerInvite).where(OrganizerInvite.token == body.token))
    invite = result.scalar_one_or_none()
    if not invite:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invalid invite token")
    if invite.accepted:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invite already used")
    if invite.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invite has expired")

    existing = await db.execute(select(User).where(User.email == invite.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")

    user = User(
        name=body.name,
        email=invite.email,
        role=UserRole.organizer,
        password_hash=_hash_password(body.password),
    )
    db.add(user)
    invite.accepted = True
    await db.commit()
    await db.refresh(user)

    token = _create_access_token(user.id, user.role.value)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserOut.model_validate(user),
    )
