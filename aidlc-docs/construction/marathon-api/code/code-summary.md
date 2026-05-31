# Code Generation Summary — marathon-api

## Files Created

### Infrastructure
- `marathon-api/requirements.txt` — pinned dependencies (fastapi, uvicorn, sqlalchemy[asyncio], asyncpg, alembic, pydantic[email], pydantic-settings, python-jose[cryptography], passlib[bcrypt], python-multipart, redis, celery, boto3, httpx)
- `marathon-api/.env.example` — template with all required env vars (no real secrets)
- `marathon-api/.env` — Docker Compose runtime config (uses Docker service hostnames)
- `marathon-api/alembic.ini` — Alembic configuration
- `marathon-api/Dockerfile` — Python 3.11-slim, installs deps, runs uvicorn on port 8000
- `marathon-api/docker-compose.yml` — postgres:15, redis:7-alpine, minio/minio, api; postgres healthcheck gates api startup

### Application Core
- `marathon-api/app/__init__.py`
- `marathon-api/app/main.py` — FastAPI app, CORS middleware, includes auth + events routers, /health endpoint
- `marathon-api/app/config.py` — pydantic-settings Settings class, loads from .env
- `marathon-api/app/database.py` — async engine (asyncpg), AsyncSessionLocal factory, get_db dependency

### Models
- `marathon-api/app/models/base.py` — DeclarativeBase + TimestampMixin (id UUID PK, created_at TIMESTAMPTZ)
- `marathon-api/app/models/user.py` — User model + UserRole enum
- `marathon-api/app/models/event.py` — Event model with JSONB fields
- `marathon-api/app/models/registration.py` — Registration model + RegistrationStatus enum, UNIQUE(event_id, user_id)
- `marathon-api/app/models/notification.py` — Notification model + NotificationChannel + NotificationTriggerType enums
- `marathon-api/app/models/task.py` — Task model + TaskCategory + TaskStatus enums, JSONB checklist
- `marathon-api/app/models/volunteer_assignment.py` — VolunteerAssignment model + VolunteerRoleType enum, UNIQUE(event_id, user_id)
- `marathon-api/app/models/__init__.py` — exports all models for Alembic discovery

### Schemas
- `marathon-api/app/schemas/__init__.py`
- `marathon-api/app/schemas/auth.py` — RegisterRequest, LoginRequest, UserOut, TokenResponse
- `marathon-api/app/schemas/event.py` — EventCreate, EventOut

### Dependencies
- `marathon-api/app/dependencies.py` — get_current_user (JWT decode → User ORM), require_role(allowed_roles) factory

### Routers
- `marathon-api/app/routers/__init__.py`
- `marathon-api/app/routers/auth.py` — POST /auth/register, POST /auth/login
- `marathon-api/app/routers/events.py` — GET /events/{event_id}

### Alembic
- `marathon-api/alembic/__init__.py`
- `marathon-api/alembic/env.py` — async Alembic env using async_engine_from_config
- `marathon-api/alembic/versions/001_initial_schema.py` — creates all 7 enums + 6 tables in one migration

## Acceptance Criteria Coverage

| AC | Description | Implementation |
|----|-------------|----------------|
| AC-1 | docker-compose up --build starts all services | docker-compose.yml with healthchecks |
| AC-2 | alembic upgrade head creates all tables | 001_initial_schema.py |
| AC-3 | POST /auth/register returns 200 with access_token | routers/auth.py register() |
| AC-4 | POST /auth/login with wrong password returns 401 | routers/auth.py login() |
| AC-5 | GET /events/{id} with valid UUID returns event JSON | routers/events.py get_event() |
| AC-6 | GET /events/{id} with invalid UUID returns 404 | routers/events.py get_event() |
| AC-7 | Protected route without token returns 401 | dependencies.py get_current_user() |
| AC-8 | Organizer route called by participant returns 403 | dependencies.py require_role() |
| AC-9 | /docs shows all routes with correct schemas | FastAPI auto-generated Swagger UI |
