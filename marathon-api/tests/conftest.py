"""
Pytest configuration — in-memory SQLite async DB, no real Celery/MinIO/SMTP.
All external side-effects (Celery tasks, MinIO uploads, SMTP) are mocked.
"""
import asyncio
import uuid
from datetime import date, datetime, timezone
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.base import Base

# ---------------------------------------------------------------------------
# In-memory async SQLite engine (no Postgres needed for unit tests)
# ---------------------------------------------------------------------------
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest_asyncio.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    """Create all tables once per test session."""
    # Import all models so metadata is populated
    import app.models  # noqa: F401
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a fresh session, roll back after each test."""
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


# ---------------------------------------------------------------------------
# App with overridden DB dependency
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    from app.main import app
    from app.database import get_db

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    # Patch all Celery tasks and MinIO so tests are hermetic
    with (
        patch("app.workers.tasks.send_email_task.delay", return_value=None),
        patch("app.workers.tasks.send_whatsapp_task.delay", return_value=None),
        patch("app.workers.tasks.generate_certificate_task.delay", return_value=None),
        patch("app.workers.tasks.send_broadcast_task.delay", return_value=None),
        patch("app.services.storage_service.upload_file", return_value="qr/test.png"),
        patch("app.services.storage_service.get_presigned_url", return_value="http://minio/presigned"),
        patch("app.services.storage_service.ensure_bucket_exists", return_value=None),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            yield ac

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helpers — create users, events, registrations
# ---------------------------------------------------------------------------
from passlib.context import CryptContext
from sqlalchemy import select

from app.models.event import Event
from app.models.notification import Notification, NotificationChannel, NotificationTriggerType
from app.models.registration import Registration, RegistrationStatus
from app.models.user import User, UserRole

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def make_user(
    db: AsyncSession,
    email: str = "user@test.com",
    role: UserRole = UserRole.participant,
    name: str = "Test User",
) -> User:
    user = User(
        name=name,
        email=email,
        role=role,
        password_hash=_pwd.hash("password"),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def make_event(db: AsyncSession, name: str = "Test Marathon") -> Event:
    event = Event(
        name=name,
        event_date=date(2026, 6, 1),
        location="Test City",
        distances=["5K", "10K"],
        is_active=True,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


async def make_registration(
    db: AsyncSession,
    user: User,
    event: Event,
    status: RegistrationStatus = RegistrationStatus.registered,
    bib_number: str | None = None,
) -> Registration:
    reg = Registration(
        user_id=user.id,
        event_id=event.id,
        status=status,
        distance="10K",
        bib_number=bib_number,
    )
    db.add(reg)
    await db.commit()
    await db.refresh(reg)
    return reg


def get_token(user: User) -> str:
    from datetime import timedelta
    from jose import jwt
    from app.config import settings

    payload = {
        "sub": str(user.id),
        "exp": datetime.now(timezone.utc) + timedelta(days=1),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def auth_headers(user: User) -> dict:
    return {"Authorization": f"Bearer {get_token(user)}"}
