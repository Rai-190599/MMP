# Requirements Document — Marathon Management Platform Sprint 1

## Intent Analysis Summary

- **User Request**: Build Sprint 1 foundation and infrastructure for a Marathon Management Platform
- **Request Type**: New Project (Greenfield)
- **Scope Estimate**: System-wide — full backend API, database schema, auth, Docker infrastructure
- **Complexity Estimate**: Complex — multiple models, async SQLAlchemy, JWT auth, Docker Compose, Alembic migrations

---

## Functional Requirements

### FR-01: User Registration
- System shall accept registration for roles: `participant`, `volunteer` (organizer created separately)
- Registration fields: name, email, phone, password, role, distance (optional), tshirt_size (optional), emergency_contact (optional), event_id (optional)
- Password shall be hashed using passlib bcrypt
- On successful registration, a JWT token (7-day expiry) shall be returned
- If role=participant and event_id is provided, a registration record shall be created with status=`registered`
- System shall log "would send welcome email to {email}" (stub — real sending in Sprint 2)

### FR-02: User Login
- System shall accept email + password credentials
- System shall verify password against stored bcrypt hash
- On success, return JWT token with same shape as registration response
- On failure (wrong password), return HTTP 401

### FR-03: Event Public Endpoint
- System shall expose GET /events/{event_id} without authentication
- Response shall include: id, name, event_date, location, distances, sponsor_tiers, faq, is_active
- Invalid UUID shall return HTTP 404

### FR-04: JWT Authentication Dependency
- All protected routes shall require `Authorization: Bearer <token>` header
- Missing or invalid token shall return HTTP 401
- Decoded token shall provide current user object

### FR-05: Role-Based Access Control
- `require_role(allowed_roles)` dependency factory shall enforce role restrictions
- Unauthorized role access shall return HTTP 403

### FR-06: Database Models
All models shall be implemented exactly per the specified schema:
- **users**: id, name, email (unique), phone, role, password_hash, created_at
- **events**: id, name, event_date, location, distances (JSONB), sponsor_tiers (JSONB), faq (JSONB), is_active, created_at
- **registrations**: id, event_id (FK), user_id (FK), status, distance, tshirt_size, emergency_contact, bib_number (unique, nullable), qr_code_url, finish_time, certificate_url, confirmed_at, bib_collected_at, created_at; UNIQUE(event_id, user_id)
- **notifications**: id, registration_id (FK), channel, trigger_type, content, sent, sent_at, created_at
- **tasks**: id, event_id (FK), assignee_id (FK, nullable), title, category, status, deadline, checklist (JSONB), created_at
- **volunteer_assignments**: id, event_id (FK), user_id (FK), role_type, category, created_at; UNIQUE(event_id, user_id)

### FR-07: Database Enums (native PostgreSQL)
- user_role: participant, organizer, volunteer
- registration_status: registered, approved, participation_confirmed, bib_collected, finished_certified
- notification_channel: email, sms, whatsapp
- notification_trigger_type: status_change, manual_broadcast
- task_category: sponsors, tshirt, bib, volunteers, logistics
- task_status: todo, in_progress, done
- volunteer_role_type: registration_desk, finish_line, general

### FR-08: Alembic Migration
- Single migration file `001_initial_schema.py` shall create all tables and enums
- `alembic upgrade head` shall succeed against a fresh PostgreSQL 15 instance

### FR-09: Docker Compose Infrastructure
- Services: postgres:15, redis:7-alpine, minio/minio, api
- API service shall wait for postgres healthcheck before starting
- MinIO ports: 9000 (API) + 9001 (console)
- All services shall start with `docker-compose up --build` without errors

---

## Non-Functional Requirements

### NFR-01: Async Database Operations
- All DB operations shall use AsyncSession (SQLAlchemy async)
- Engine shall use asyncpg driver

### NFR-02: Configuration Management
- All secrets and config via pydantic-settings loaded from .env file
- Settings: DATABASE_URL, REDIS_URL, SECRET_KEY, MINIO_*, SMTP_*

### NFR-03: API Documentation
- FastAPI Swagger UI (/docs) shall display all routes with correct schemas

### NFR-04: Code Conventions
- All models inherit from Base with id (UUID, default uuid4) and created_at (DateTime, server_default)
- All routers use APIRouter with prefix and tags
- All schemas use Pydantic BaseModel with model_config = ConfigDict(from_attributes=True)
- Error handling via HTTPException with clear detail strings

### NFR-05: Security
- JWT signed with SECRET_KEY, algorithm HS256
- Passwords never stored in plaintext
- .env.example provided (no real secrets committed)

### NFR-06: File Structure
- Must match exactly the specified structure under marathon-api/

---

## Extension Configuration

| Extension | Enabled | Decided At |
|---|---|---|
| Security Baseline | Yes (implicit — production-grade auth system) | Requirements Analysis |
| Property-Based Testing | No (Sprint 1 is foundation/infrastructure) | Requirements Analysis |

---

## Acceptance Criteria

1. `docker-compose up --build` starts all services with no errors
2. `alembic upgrade head` creates all tables and enums in postgres
3. POST /auth/register with valid body returns 200 with access_token
4. POST /auth/login with wrong password returns 401
5. GET /events/{id} with valid UUID returns event JSON
6. GET /events/{id} with invalid UUID returns 404
7. A protected route called without token returns 401
8. A route requiring organizer role called by participant returns 403
9. /docs (Swagger UI) shows all routes with correct schemas
