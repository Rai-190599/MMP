import uuid
from datetime import date

import pytest
from jose import jwt
from sqlalchemy import select

from app.config import settings
from app.models.event import Event
from app.models.registration import Registration
from app.models.user import User, UserRole
from tests.conftest import auth_headers, make_event, make_user


@pytest.mark.asyncio
async def test_signup_creates_participant_and_returns_jwt(client, db):
    resp = await client.post(
        "/auth/signup",
        json={
            "name": "New Runner",
            "email": "new.runner@test.com",
            "phone": "1234567890",
            "password": "password123",
        },
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "new.runner@test.com"
    assert data["user"]["role"] == "participant"

    payload = jwt.decode(
        data["access_token"],
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM],
    )
    assert payload["sub"] == data["user"]["id"]
    assert payload["role"] == "participant"


@pytest.mark.asyncio
async def test_signup_existing_email_returns_409(client, db):
    await make_user(db, "taken@test.com", UserRole.participant)

    resp = await client.post(
        "/auth/signup",
        json={
            "name": "Taken Email",
            "email": "taken@test.com",
            "phone": "1234567890",
            "password": "password123",
        },
    )

    assert resp.status_code == 409
    assert resp.json()["detail"] == "Email already in use"


@pytest.mark.asyncio
async def test_signup_ignores_role_field(client, db):
    resp = await client.post(
        "/auth/signup",
        json={
            "name": "Role Sneak",
            "email": "role.sneak@test.com",
            "phone": "1234567890",
            "password": "password123",
            "role": "organizer",
        },
    )

    assert resp.status_code == 201
    assert resp.json()["user"]["role"] == "participant"

    result = await db.execute(select(User).where(User.email == "role.sneak@test.com"))
    user = result.scalar_one()
    assert user.role == UserRole.participant


@pytest.mark.asyncio
async def test_join_creates_registration_for_authenticated_participant(client, db):
    user = await make_user(db, "joiner@test.com", UserRole.participant, "Joiner")
    event = await make_event(db)

    resp = await client.post(
        "/registrations/join",
        json={
            "event_id": str(event.id),
            "distance": "10K",
            "tshirt_size": "M",
            "emergency_contact": "Jane 1234567890",
        },
        headers=auth_headers(user),
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["event_id"] == str(event.id)
    assert data["user_id"] == str(user.id)
    assert data["status"] == "registered"
    assert data["distance"] == "10K"
    assert data["tshirt_size"] == "M"
    assert data["emergency_contact"] == "Jane 1234567890"


@pytest.mark.asyncio
async def test_join_without_auth_returns_401(client, db):
    event = await make_event(db)

    resp = await client.post(
        "/registrations/join",
        json={
            "event_id": str(event.id),
            "distance": "10K",
            "tshirt_size": "M",
            "emergency_contact": "Jane 1234567890",
        },
    )

    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_join_inactive_event_returns_400(client, db):
    user = await make_user(db, "inactive@test.com", UserRole.participant, "Inactive")
    event = Event(
        name="Closed Marathon",
        event_date=date(2026, 7, 1),
        location="Closed City",
        distances=["10K"],
        is_active=False,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)

    resp = await client.post(
        "/registrations/join",
        json={
            "event_id": str(event.id),
            "distance": "10K",
            "tshirt_size": "M",
            "emergency_contact": "Jane 1234567890",
        },
        headers=auth_headers(user),
    )

    assert resp.status_code == 400
    assert resp.json()["detail"] == "Event is inactive"


@pytest.mark.asyncio
async def test_join_duplicate_event_registration_returns_409(client, db):
    user = await make_user(db, "dupe@test.com", UserRole.participant, "Dupe")
    event = await make_event(db)

    payload = {
        "event_id": str(event.id),
        "distance": "10K",
        "tshirt_size": "M",
        "emergency_contact": "Jane 1234567890",
    }

    first = await client.post("/registrations/join", json=payload, headers=auth_headers(user))
    second = await client.post("/registrations/join", json=payload, headers=auth_headers(user))

    assert first.status_code == 201
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_legacy_register_and_registration_endpoints_still_work(client, db):
    event = await make_event(db)

    register_resp = await client.post(
        "/auth/register",
        json={
            "name": "Legacy Runner",
            "email": "legacy.runner@test.com",
            "phone": "1234567890",
            "password": "password123",
            "role": "participant",
            "event_id": str(event.id),
            "distance": "5K",
            "tshirt_size": "S",
            "emergency_contact": "Legacy 1234567890",
        },
    )
    assert register_resp.status_code == 200

    result = await db.execute(
        select(Registration).where(
            Registration.event_id == event.id,
            Registration.user_id == uuid.UUID(register_resp.json()["user"]["id"]),
        )
    )
    assert result.scalar_one_or_none() is not None

    user = await make_user(db, "legacy.registration@test.com", UserRole.participant, "Legacy Reg")
    registration_resp = await client.post(
        "/registrations/",
        json={"event_id": str(event.id), "distance": "10K"},
        headers=auth_headers(user),
    )
    assert registration_resp.status_code == 201


@pytest.mark.asyncio
async def test_openapi_shows_legacy_and_new_endpoints(client):
    resp = await client.get("/openapi.json")

    assert resp.status_code == 200
    paths = resp.json()["paths"]
    assert "/auth/register" in paths
    assert "/auth/signup" in paths
    assert "/registrations/" in paths
    assert "/registrations/join" in paths

    assert "SignupRequest" in resp.text
    assert "SignupResponse" in resp.text
    assert "EventRegistrationRequest" in resp.text
