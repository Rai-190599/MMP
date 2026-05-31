# Marathon Management Platform — Agent README

> **Purpose of this document:** This README is the single source of truth for any AI agent, developer, or tool working on this codebase. Read it fully before making any change. It covers architecture, conventions, data flow, business rules, and how to safely extend the project.

---

## Table of contents

1. [Project overview](#1-project-overview)
2. [Tech stack](#2-tech-stack)
3. [Repository structure](#3-repository-structure)
4. [Architecture overview](#4-architecture-overview)
5. [Database schema](#5-database-schema)
6. [Business rules and domain logic](#6-business-rules-and-domain-logic)
7. [API reference](#7-api-reference)
8. [Authentication and authorization](#8-authentication-and-authorization)
9. [Background jobs (Celery)](#9-background-jobs-celery)
10. [File storage (MinIO)](#10-file-storage-minio)
11. [Notification system](#11-notification-system)
12. [Frontend structure](#12-frontend-structure)
13. [Coding conventions](#13-coding-conventions)
14. [Environment variables](#14-environment-variables)
15. [Docker and local setup](#15-docker-and-local-setup)
16. [How to add a new feature](#16-how-to-add-a-new-feature)
17. [What never to change](#17-what-never-to-change)
18. [Known design decisions and why](#18-known-design-decisions-and-why)

---

## 1. Project overview

A full-stack platform to manage marathon events end-to-end. Three types of people use it:

| Role | What they do |
|------|-------------|
| **Admin** | Created via seed script. Invites organizers. Views everything. |
| **Organizer** | Invited by admin. Creates events. Approves registrations. Assigns BIBs. Manages tasks and volunteers. |
| **Participant** | Self-registers an account. Browses events. Registers for an event. Tracks their status. Downloads certificate. |

A participant can also **apply to volunteer** for a specific event after their registration is approved. Volunteering is a per-event role, not a permanent identity.

### Core participant journey (5 stages)

```
[1] Registered
      ↓ organizer approves + assigns BIB number
[2] Approved & BIB assigned
      ↓ participant clicks "Confirm participation"
[3] Participation confirmed  ← WhatsApp group invite sent here
      ↓ volunteer scans QR code at event entry
[4] BIB collected
      ↓ organizer enters finish time
[5] Finished & certified  ← PDF certificate auto-generated
```

Each transition triggers an automatic notification. The stage number is always derived from the `status` enum value — never stored separately.

---

## 2. Tech stack

### Backend
| Component | Technology | Version |
|-----------|-----------|---------|
| Language | Python | 3.11 |
| Framework | FastAPI | latest |
| ORM | SQLAlchemy (async) | 2.x |
| Migrations | Alembic | latest |
| Validation | Pydantic | v2 |
| Auth | python-jose (JWT) + passlib bcrypt | latest |
| Task queue | Celery | latest |
| Task broker | Redis | 7 |
| Config | pydantic-settings (.env) | latest |
| PDF generation | WeasyPrint | latest |
| QR generation | qrcode[pil] | latest |
| WhatsApp/SMS | Twilio (optional) | latest |
| Email | smtplib (or fastapi-mail) | stdlib |

### Frontend
| Component | Technology |
|-----------|-----------|
| Framework | React 18 + Vite |
| Routing | react-router-dom v6 |
| HTTP | axios |
| Auth state | React Context + localStorage |
| Styling | Plain CSS modules |
| QR scanning | html5-qrcode |

### Infrastructure (Docker)
| Service | Image | Port |
|---------|-------|------|
| postgres | postgres:15 | 5432 |
| redis | redis:7-alpine | 6379 |
| minio | minio/minio | 9000, 9001 |
| api | custom (Dockerfile) | 8000 |
| celery_worker | same Dockerfile | — |
| celery_beat | same Dockerfile | — |
| flower | mher/flower | 5555 |
| frontend | node:18 | 3000 |

---

## 3. Repository structure

```
marathon-api/                        ← FastAPI backend
├── app/
│   ├── main.py                      ← App entry point, router registration, CORS, startup hooks
│   ├── config.py                    ← All env vars via pydantic-settings (Settings class)
│   ├── database.py                  ← Async SQLAlchemy engine, AsyncSession, get_db dependency
│   ├── dependencies.py              ← get_current_user, require_role(roles)
│   │
│   ├── models/                      ← SQLAlchemy ORM models (one file per table)
│   │   ├── __init__.py              ← Exports all models (Alembic needs this)
│   │   ├── base.py                  ← Base class with id (UUID PK) + created_at
│   │   ├── user.py
│   │   ├── event.py
│   │   ├── registration.py
│   │   ├── notification.py
│   │   ├── task.py
│   │   ├── volunteer_assignment.py
│   │   ├── volunteer_application.py ← Added in Change 2
│   │   └── organizer_invite.py      ← Added in Sprint 0
│   │
│   ├── schemas/                     ← Pydantic request/response schemas
│   │   ├── auth.py                  ← SignupRequest, LoginRequest, TokenResponse, UserOut
│   │   ├── event.py                 ← EventOut, EventCreateRequest, EventUpdateRequest, EventDetail
│   │   ├── registration.py          ← RegistrationOut, EventRegistrationRequest, StatusPageOut
│   │   ├── task.py                  ← TaskOut, TaskCreate, TaskUpdate
│   │   ├── notification.py          ← BroadcastRequest, NotificationLogOut
│   │   ├── admin.py                 ← InviteCreateRequest, InviteOut, AcceptInviteRequest
│   │   └── volunteer.py             ← VolunteerApplyRequest, VolunteerApplicationOut, VolunteerSlotsOut
│   │
│   ├── routers/                     ← One file per feature domain
│   │   ├── auth.py                  ← /auth/signup, /auth/login, /auth/accept-invite
│   │   ├── events.py                ← /events (public list + detail)
│   │   ├── event_mgmt.py            ← /manage/events (organizer CRUD)
│   │   ├── registrations.py         ← /registrations (participant self-service)
│   │   ├── organizer.py             ← /organizer/* (dashboard, approvals, finish times)
│   │   ├── notifications.py         ← /notifications/broadcast, /notifications/history
│   │   ├── tasks.py                 ← /tasks (organizer task board)
│   │   ├── volunteers.py            ← /volunteers/scan, /volunteers/me/assignment
│   │   ├── volunteer_apply.py       ← /volunteer-applications (participant apply flow)
│   │   ├── certificates.py          ← /certificates/{reg_id}
│   │   └── admin.py                 ← /admin/* (admin only)
│   │
│   ├── services/                    ← Business logic (called by routers)
│   │   ├── registration_service.py  ← create, status transitions, confirm, assign_bib, finish_time
│   │   ├── notification_service.py  ← send_email(), send_whatsapp() with stub fallback
│   │   ├── bib_service.py           ← QR code generation + MinIO upload
│   │   ├── certificate_service.py   ← PDF generation + MinIO upload
│   │   └── storage_service.py       ← MinIO upload/download/presigned URLs
│   │
│   ├── workers/
│   │   ├── celery_app.py            ← Celery instance (broker=Redis)
│   │   └── tasks.py                 ← send_email_task, send_whatsapp_task, generate_certificate_task
│   │
│   └── utils/
│       ├── qr.py                    ← generate_qr_png(data) → bytes
│       └── pdf.py                   ← generate_certificate_pdf(...) → bytes
│
├── alembic/
│   ├── env.py                       ← Async Alembic env
│   └── versions/                    ← Migration files in order
│       ├── 001_initial_schema.py
│       ├── 002_sprint0_additions.py  ← admin role, organizer_invites, event_organizers
│       └── 003_volunteer_refactor.py ← remove volunteer from user_role, volunteer_applications, slot_caps
│
├── scripts/
│   └── seed_admin.py                ← One-time admin creation script (idempotent)
│
├── docker-compose.yml
├── Dockerfile
├── alembic.ini
├── requirements.txt
└── .env.example

marathon-frontend/                   ← React frontend
├── src/
│   ├── main.jsx
│   ├── App.jsx                      ← All routes + AuthContext wrapper
│   ├── api/
│   │   └── client.js                ← axios instance with JWT interceptor
│   ├── context/
│   │   └── AuthContext.jsx          ← { user, token, login, logout }
│   ├── hooks/
│   │   ├── useAuth.js
│   │   └── useApi.js                ← { data, loading, error, execute }
│   ├── pages/
│   │   ├── EventLanding.jsx         ← Public event page (legacy, pre-login)
│   │   ├── Signup.jsx               ← Account creation only (no event/role)
│   │   ├── Login.jsx
│   │   ├── EventBrowser.jsx         ← Browse all upcoming events (post-login)
│   │   ├── EventRegister.jsx        ← Register for a specific event
│   │   ├── ParticipantStatus.jsx    ← 5-stage tracker + volunteer apply section
│   │   ├── VolunteerApply.jsx       ← Apply for volunteer role on an event
│   │   ├── CertificateDownload.jsx
│   │   ├── organizer/
│   │   │   ├── Dashboard.jsx        ← Summary cards + quick actions
│   │   │   ├── Registrations.jsx    ← Table + approve + finish time
│   │   │   ├── TaskBoard.jsx        ← Kanban board
│   │   │   ├── NotificationCenter.jsx
│   │   │   ├── Events.jsx           ← Create/edit organizer's events
│   │   │   └── VolunteerApplications.jsx ← Review volunteer applicants
│   │   └── admin/
│   │       └── Dashboard.jsx        ← Users, invites, all events
│   ├── components/
│   │   ├── ProtectedRoute.jsx       ← Role-based route guard
│   │   ├── StatusTracker.jsx        ← 5-bubble progress bar
│   │   ├── Navbar.jsx
│   │   ├── LoadingSpinner.jsx
│   │   └── QRScanner.jsx            ← html5-qrcode wrapper
│   └── AcceptInvite.jsx             ← Organizer invite acceptance page
├── index.html
├── vite.config.js
└── package.json
```

---

## 4. Architecture overview

```
Browser (React SPA :3000)
        │  REST + JWT
        ▼
FastAPI (:8000)
  ├── Routers → Services → SQLAlchemy AsyncSession → PostgreSQL (:5432)
  ├── Routers → Celery .delay() → Redis (:6379) → Celery Worker
  │                                                    ├── send_email_task → SMTP / stub log
  │                                                    ├── send_whatsapp_task → Twilio / stub log
  │                                                    └── generate_certificate_task → WeasyPrint → MinIO
  └── Routers → storage_service → MinIO (:9000)
```

**Request flow for every API call:**
1. Request hits FastAPI router
2. `get_current_user` dependency decodes JWT → loads User from DB
3. `require_role(["organizer"])` dependency checks role → 403 if not allowed
4. Router calls service function (business logic lives in services, not routers)
5. Service uses `AsyncSession` for all DB operations
6. If a status change happens → service dispatches Celery task via `.delay()`
7. Router returns Pydantic schema (never raw ORM object)

---

## 5. Database schema

### Enums (native Postgres enums)

```sql
user_role:             participant | organizer | admin
registration_status:   registered | approved | participation_confirmed | bib_collected | finished_certified
notification_channel:  email | sms | whatsapp
notification_trigger:  status_change | manual_broadcast
task_category:         sponsors | tshirt | bib | volunteers | logistics
task_status:           todo | in_progress | done
volunteer_role_type:   registration_desk | finish_line | general
```

> **Critical:** `volunteer` is NOT in `user_role`. Volunteering is captured in `volunteer_assignments` and `volunteer_applications` per event. A user's role is always `participant`, `organizer`, or `admin`.

### Tables

#### users
```
id               UUID        PK, default gen_random_uuid()
name             VARCHAR(255) NOT NULL
email            VARCHAR(255) UNIQUE NOT NULL
phone            VARCHAR(20)
role             user_role   NOT NULL
password_hash    VARCHAR(255) NOT NULL
created_at       TIMESTAMPTZ server_default=now()
```

#### events
```
id                   UUID        PK
name                 VARCHAR(255) NOT NULL
event_date           DATE        NOT NULL
location             VARCHAR(500)
distances            JSONB       e.g. ["5K","10K","21K"]
sponsor_tiers        JSONB
faq                  JSONB       list of {question, answer}
is_active            BOOLEAN     default true
volunteer_slot_caps  JSONB       default {"registration_desk":5,"finish_line":3,"general":10}
created_at           TIMESTAMPTZ server_default=now()
```

#### event_organizers
```
event_id    UUID  FK→events.id ON DELETE CASCADE
user_id     UUID  FK→users.id ON DELETE CASCADE
PRIMARY KEY (event_id, user_id)
```
One organizer can own many events. One event can have multiple co-organizers.

#### registrations
```
id                UUID        PK
event_id          UUID        FK→events.id NOT NULL
user_id           UUID        FK→users.id NOT NULL
status            registration_status NOT NULL default='registered'
distance          VARCHAR(20)
tshirt_size       VARCHAR(10)
emergency_contact VARCHAR(255)
bib_number        VARCHAR(20) UNIQUE nullable
qr_code_url       TEXT        nullable (MinIO object key, not full URL)
finish_time       TIMESTAMPTZ nullable
certificate_url   TEXT        nullable (MinIO object key)
confirmed_at      TIMESTAMPTZ nullable
bib_collected_at  TIMESTAMPTZ nullable
created_at        TIMESTAMPTZ server_default=now()
UNIQUE (event_id, user_id)
```

#### notifications
```
id               UUID  PK
registration_id  UUID  FK→registrations.id
channel          notification_channel NOT NULL
trigger_type     notification_trigger NOT NULL
content          TEXT
sent             BOOLEAN default false
sent_at          TIMESTAMPTZ nullable
created_at       TIMESTAMPTZ server_default=now()
```

#### tasks
```
id           UUID  PK
event_id     UUID  FK→events.id NOT NULL
assignee_id  UUID  FK→users.id nullable
title        VARCHAR(500) NOT NULL
category     task_category NOT NULL
status       task_status NOT NULL default='todo'
deadline     DATE nullable
checklist    JSONB default='[]'   list of {item: str, done: bool}
created_at   TIMESTAMPTZ server_default=now()
```

#### volunteer_assignments
```
id           UUID  PK
event_id     UUID  FK→events.id NOT NULL
user_id      UUID  FK→users.id NOT NULL
role_type    volunteer_role_type NOT NULL
category     VARCHAR(100)
created_at   TIMESTAMPTZ server_default=now()
UNIQUE (event_id, user_id)
```
Created either by organizer directly or auto-created when a volunteer application is approved.

#### volunteer_applications
```
id            UUID  PK
event_id      UUID  FK→events.id ON DELETE CASCADE NOT NULL
user_id       UUID  FK→users.id ON DELETE CASCADE NOT NULL
desired_role  VARCHAR(50) NOT NULL  values: registration_desk | finish_line | general
status        VARCHAR(20) NOT NULL default='pending'  values: pending | approved | rejected
note          TEXT nullable
applied_at    TIMESTAMPTZ server_default=now()
reviewed_at   TIMESTAMPTZ nullable
UNIQUE (event_id, user_id)
```

#### organizer_invites
```
id           UUID  PK
email        VARCHAR(255) NOT NULL
token        UUID  UNIQUE NOT NULL default gen_random_uuid()
invited_by   UUID  FK→users.id nullable ON DELETE SET NULL
accepted     BOOLEAN default false
expires_at   TIMESTAMPTZ NOT NULL (now() + 7 days)
created_at   TIMESTAMPTZ server_default=now()
```

---

## 6. Business rules and domain logic

### Registration status transitions
These are enforced in `registration_service.py`. No router should change status directly.

```
registered → approved
  Trigger: organizer calls PATCH /organizer/registrations/{id}/approve
  Side effect: BIB number assigned, QR code generated and stored in MinIO, email sent

approved → participation_confirmed
  Trigger: participant calls POST /registrations/me/confirm
  Side effect: WhatsApp group invite sent

participation_confirmed → bib_collected
  Trigger: volunteer calls POST /volunteers/scan with QR data
  Side effect: bib_collected_at timestamp set, email sent
  Safety: SELECT FOR UPDATE lock on registration row (prevents race condition)

bib_collected → finished_certified
  Trigger: organizer calls PATCH /organizer/registrations/{id}/finish-time
  Side effect: Celery task dispatched to generate PDF certificate and upload to MinIO
```

**No backward transitions are allowed.** Any attempt to go backward returns HTTP 400.

### BIB number
- Assigned manually by organizer (not auto-generated)
- Must be unique across the entire platform (UNIQUE constraint on registrations.bib_number)
- Format: flexible VARCHAR(20) — organizer decides the format (e.g. "101", "5K-042")
- QR code encodes the registration UUID (not the BIB number)

### QR code
- Generated when BIB is assigned (status approved)
- Encodes: `str(registration.id)` — the UUID string
- Stored in MinIO as: `qr/{registration_id}.png`
- `registrations.qr_code_url` stores the MinIO object key (NOT a full URL)
- Full URL is generated on-demand via `storage_service.get_presigned_url()`

### Certificate PDF
- Generated asynchronously via Celery after finish time is entered
- Contains: participant name, BIB number, distance, finish time, event name, event date
- Stored in MinIO as: `certificates/{registration_id}.pdf`
- `GET /certificates/{reg_id}` returns 202 while generating, 200 with presigned URL once ready
- Presigned URL valid for 7 days

### Volunteer slot cap enforcement
- Each event has `volunteer_slot_caps` JSONB: `{"registration_desk": 5, "finish_line": 3, "general": 10}`
- When a participant applies: count approved applications for that role → block if at cap
- When organizer approves: re-check cap (race condition safety) → block if another was approved first
- On approval: automatically create a `volunteer_assignments` row
- Prerequisite: user must have a registration with status >= `approved` to apply as volunteer

### Organizer event ownership
- Checked via `event_organizers` table
- Organizer can only manage events where `(event_id, user_id)` exists in `event_organizers`
- Admin bypasses this check (can manage all events)
- Always verify ownership in organizer routes before any write operation

### Admin account
- Created ONLY via `scripts/seed_admin.py` — never via any API endpoint
- `POST /auth/signup` always creates `role=participant`, never admin or organizer
- Organizer accounts created only via invite flow (`POST /auth/accept-invite`)

---

## 7. API reference

### Auth routes (`/auth`)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/signup` | None | Create participant account (name, email, phone, password only) |
| POST | `/auth/login` | None | Login → JWT |
| POST | `/auth/accept-invite` | None | Organizer accepts invite token → creates organizer account |

### Public event routes (`/events`)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/events` | None | List active upcoming events (paginated) |
| GET | `/events/{id}` | None | Single event (legacy) |
| GET | `/events/{id}/detail` | Optional | Event detail + user registration status + slot counts |

### Participant registration (`/registrations`)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/registrations/join` | Participant | Register for an event |
| GET | `/registrations/me` | Participant | Status page data (query: event_id) |
| POST | `/registrations/me/confirm` | Participant | Confirm participation (stage 2→3) |
| GET | `/registrations/{id}/qr` | Participant | Presigned QR code URL |

### Organizer dashboard (`/organizer`)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/organizer/registrations` | Organizer | Table with filters + pagination |
| GET | `/organizer/registrations/summary` | Organizer | Count by status |
| PATCH | `/organizer/registrations/{id}/approve` | Organizer | Assign BIB → stage 1→2 |
| PATCH | `/organizer/registrations/{id}/finish-time` | Organizer | Enter finish time → stage 4→5 |
| POST | `/organizer/registrations/upload-finish-times` | Organizer | Bulk CSV upload |
| GET | `/organizer/volunteer-applications` | Organizer | List volunteer applicants |
| PATCH | `/organizer/volunteer-applications/{id}` | Organizer | Approve or reject applicant |

### Event management (`/manage/events`)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/manage/events` | Organizer/Admin | List events (organizer sees own; admin sees all) |
| POST | `/manage/events` | Organizer/Admin | Create event |
| PATCH | `/manage/events/{id}` | Organizer/Admin | Update event (organizer must own it) |
| POST | `/manage/events/{id}/co-organizer` | Organizer/Admin | Add co-organizer |

### Notifications (`/notifications`)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/notifications/broadcast` | Organizer | Manual broadcast (email/WhatsApp/SMS) |
| GET | `/notifications/history` | Organizer | Notification log |

### Tasks (`/tasks`)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/tasks` | Organizer | List by event, grouped by status |
| POST | `/tasks` | Organizer | Create task |
| PATCH | `/tasks/{id}` | Organizer | Update task |
| DELETE | `/tasks/{id}` | Organizer | Delete task |
| PATCH | `/tasks/{id}/checklist` | Organizer | Toggle checklist item |

### Volunteer flows (`/volunteers`, `/volunteer-applications`)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/volunteers/scan` | Volunteer | QR scan → stage 3→4 |
| GET | `/volunteers/me/assignment` | Volunteer | My assigned role + event |
| POST | `/volunteer-applications` | Participant | Apply to volunteer |
| GET | `/volunteer-applications/me` | Participant | My applications |
| DELETE | `/volunteer-applications/{id}` | Participant | Withdraw pending application |
| GET | `/volunteer-applications/event/{id}/slots` | None | Live slot counts |

### Certificates (`/certificates`)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/certificates/{reg_id}` | Participant (owner) | 202 if generating, 200 with download URL |

### Admin (`/admin`)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/admin/invites` | Admin | Send organizer invite |
| GET | `/admin/invites` | Admin | List all invites |
| GET | `/admin/users` | Admin | All users with role filter |
| GET | `/admin/events` | Admin | All events with organizer names |

---

## 8. Authentication and authorization

### JWT structure
```json
{
  "sub": "<user_id as string>",
  "role": "participant | organizer | admin",
  "exp": "<unix timestamp>"
}
```
Token expiry: 7 days. Stored in `localStorage` on the frontend.

### Dependencies (backend)
```python
# In app/dependencies.py

get_current_user
  → Reads Authorization: Bearer <token>
  → Decodes JWT via python-jose
  → Loads User from DB by sub (user_id)
  → Returns User ORM object
  → 401 if no token or invalid token

require_role(allowed_roles: list[str])
  → Dependency factory
  → Calls get_current_user first
  → Raises 403 if user.role not in allowed_roles
  → Usage: Depends(require_role(["organizer", "admin"]))
```

### Frontend route guards
`ProtectedRoute.jsx` reads `user` from `AuthContext`. If no user → redirect to `/login`. If user role doesn't match the required role prop → redirect to appropriate home page.

### Post-login redirects
```
admin       → /admin
organizer   → /organizer/events
participant → /events
volunteer (scanner role) → /volunteer/scanner
```

---

## 9. Background jobs (Celery)

All tasks defined in `app/workers/tasks.py`. Broker and result backend: Redis.

### Task: `send_email_task(to_email, subject, body_html)`
- If `SMTP_HOST` is set: sends real email via smtplib
- If not set: logs `[EMAIL STUB] To: {email}, Subject: {subject}`
- Always creates a `Notification` row in DB with `sent=True/False`
- Never raises — on failure, logs error and marks `sent=False`

### Task: `send_whatsapp_task(to_phone, message)`
- If `TWILIO_ACCOUNT_SID` + `TWILIO_AUTH_TOKEN` set: sends via Twilio WhatsApp API
- If not set: logs `[WHATSAPP STUB] To: {phone}`
- Always creates a `Notification` row

### Task: `generate_certificate_task(registration_id: str)`
- Fetches registration + user + event from DB (uses `asyncio.run` inside sync Celery task)
- Generates PDF via `utils/pdf.py` (WeasyPrint HTML→PDF)
- Uploads to MinIO: `certificates/{registration_id}.pdf`
- Updates `registrations.certificate_url`
- Dispatches `send_email_task` with presigned download URL (valid 7 days)

### When tasks are dispatched
| Event | Task dispatched |
|-------|----------------|
| Registration created (stage 1) | `send_email_task` — confirmation |
| BIB assigned (stage 2) | `send_email_task` — BIB notification |
| Participation confirmed (stage 3) | `send_whatsapp_task` — group invite |
| BIB collected (stage 4) | `send_email_task` — see you at start line |
| Finish time entered (stage 5) | `generate_certificate_task` |
| Manual broadcast | `send_email_task` or `send_whatsapp_task` per recipient |
| Volunteer application approved | `send_email_task` — approval notification |

---

## 10. File storage (MinIO)

MinIO is S3-compatible and runs in Docker. Bucket name: `marathon` (auto-created on startup).

### Object naming convention
```
qr/{registration_id}.png            ← BIB QR codes
certificates/{registration_id}.pdf  ← Participation certificates
```

### Storage service (`app/services/storage_service.py`)
```python
upload_file(file_bytes, object_name, content_type) → str
  # Uploads to MinIO, returns object_name

get_presigned_url(object_name, expires_in_seconds=3600) → str
  # Returns presigned GET URL for temporary access

ensure_bucket_exists() → None
  # Called on FastAPI startup
```

### Important
- `registrations.qr_code_url` and `registrations.certificate_url` store the **object key** (e.g. `qr/abc.png`), NOT the full URL.
- Full URLs are always generated on-demand via `get_presigned_url()`.
- Never store full presigned URLs in the DB — they expire.

---

## 11. Notification system

### Auto notifications (status-driven)
Every status transition in `registration_service.py` calls the appropriate Celery task. The `Notification` table is the audit log.

### Manual broadcast
`POST /notifications/broadcast` — organizer composes a message, chooses channel (email/whatsapp/sms), optionally filters by registration status. Capped at 500 recipients per broadcast.

### Notification content by stage
| Stage | Channel | Content |
|-------|---------|---------|
| registered | Email | "Registration confirmed for {event}" |
| approved | Email | "You're approved! BIB #{bib_number}" |
| participation_confirmed | WhatsApp | "Welcome to {event} WhatsApp group! [link]" |
| bib_collected | Email | "BIB collected. See you at the start!" |
| finished_certified | Email | "Certificate ready" + download link |

---

## 12. Frontend structure

### AuthContext
Single source of truth for authentication state.
```javascript
// Available everywhere via useAuth()
{
  user: { id, role, name },  // decoded from JWT
  token: string,
  isAuthenticated: boolean,
  login(token),   // stores token, decodes user, sets state
  logout()        // clears localStorage, redirects to /login
}
```

### API client (`src/api/client.js`)
Axios instance with:
- `baseURL`: `import.meta.env.VITE_API_URL` (e.g. `http://localhost:8000`)
- Request interceptor: adds `Authorization: Bearer {token}` if token exists
- Response interceptor: on 401 → calls `logout()` and redirects to `/login`

### Route structure
```
/                           → EventLanding (public, legacy)
/signup                     → Signup (public)
/login                      → Login (public)
/accept-invite?token=...    → AcceptInvite (public)
/events                     → EventBrowser (participant)
/events/:id/register        → EventRegister (participant)
/events/:id/volunteer       → VolunteerApply (participant)
/status                     → ParticipantStatus (participant, query: ?event_id=)
/certificate/:regId         → CertificateDownload (participant)
/organizer                  → Dashboard (organizer)
/organizer/events           → Events list + create (organizer)
/organizer/registrations    → Registrations table (organizer)
/organizer/tasks            → TaskBoard (organizer)
/organizer/notifications    → NotificationCenter (organizer)
/organizer/volunteer-applications → VolunteerApplications (organizer)
/volunteer/scanner          → Scanner (assigned volunteer)
/admin                      → AdminDashboard (admin)
```

### useApi hook
Generic data fetching hook used across all components:
```javascript
const { data, loading, error, execute } = useApi();
// execute(apiCallFn) triggers the call and manages state
```

---

## 13. Coding conventions

These conventions are **non-negotiable**. Every new file must follow them exactly.

### Backend conventions

**Models**
```python
# Always inherit from Base (has id + created_at)
class MyModel(Base):
    __tablename__ = "my_table"
    # id and created_at come from Base
    name: Mapped[str] = mapped_column(String(255))
```

**Schemas**
```python
# Always use ConfigDict(from_attributes=True) for ORM compatibility
class MySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
```

**Routers**
```python
# Always use APIRouter with prefix and tags
router = APIRouter(prefix="/my-feature", tags=["my-feature"])

# Always return Pydantic schema, never raw ORM object
@router.get("/{id}", response_model=MySchema)
async def get_thing(id: UUID, db: AsyncSession = Depends(get_db)):
    ...
```

**Services**
```python
# Business logic always goes in services, not routers
# All service functions are async and take db: AsyncSession as first arg
async def do_business_thing(db: AsyncSession, ...) -> MyModel:
    ...
```

**Error handling**
```python
# Always raise HTTPException with a clear detail string
raise HTTPException(status_code=404, detail="Registration not found")
raise HTTPException(status_code=400, detail="Cannot transition from approved to registered")
raise HTTPException(status_code=409, detail="User already registered for this event")
```

**DB queries**
```python
# Use async SQLAlchemy 2.x syntax
result = await db.execute(select(User).where(User.email == email))
user = result.scalar_one_or_none()
```

**Celery task dispatch**
```python
# Always use .delay() — never call tasks synchronously in request handlers
send_email_task.delay(to_email, subject, body_html)
```

### Frontend conventions

**API calls** — always go through `src/api/client.js`, never use `fetch` directly.

**State** — use React `useState` for component state. Only `AuthContext` uses React Context. No Redux, no Zustand.

**No UI library** — plain CSS modules only. No Tailwind, no styled-components, no MUI.

**Forms** — use controlled inputs with `useState`. No form libraries. No `<form>` tags with `onSubmit` in React — use `<button onClick={handleSubmit}>`.

**Protected routes** — always wrap protected pages in `<ProtectedRoute role="participant">` etc. Never check auth inside the page component itself.

**Error display** — show API error messages inline near the relevant field or at the top of the form. Never use `alert()`.

---

## 14. Environment variables

All defined in `.env` (backend) and `.env` (frontend). See `.env.example` for defaults.

### Backend (`.env`)
```bash
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/marathon

# Redis
REDIS_URL=redis://redis:6379/0

# JWT
SECRET_KEY=your-secret-key-here-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRE_DAYS=7

# Admin seed (used only by scripts/seed_admin.py)
ADMIN_EMAIL=admin@marathon.com
ADMIN_PASSWORD=changeme123
ADMIN_NAME=Platform Admin

# MinIO / S3
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=admin
MINIO_SECRET_KEY=password123
MINIO_BUCKET=marathon
MINIO_USE_SSL=false

# Email (optional — if not set, emails are logged to console)
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=noreply@marathon.com

# WhatsApp / SMS (optional — if not set, messages are logged to console)
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
```

### Frontend (`.env`)
```bash
VITE_API_URL=http://localhost:8000
```

**Behavior when optional vars are not set:**
- No `SMTP_*`: emails logged as `[EMAIL STUB] To: ...` in Celery worker console
- No `TWILIO_*`: WhatsApp messages logged as `[WHATSAPP STUB] To: ...`
- Everything else works normally — stubs do not throw errors

---

## 15. Docker and local setup

### First-time setup
```bash
# 1. Copy env file
cp .env.example .env

# 2. Start all services
docker-compose up --build -d

# 3. Run migrations
docker-compose exec api alembic upgrade head

# 4. Seed admin account
docker-compose exec api python scripts/seed_admin.py

# 5. Verify MinIO bucket (auto-created on startup)
# Open http://localhost:9001 — login: admin / password123
```

### Service URLs
```
API:           http://localhost:8000
API docs:      http://localhost:8000/docs
Frontend:      http://localhost:3000
MinIO console: http://localhost:9001
Flower:        http://localhost:5555  (Celery monitor)
```

### Adding a new migration
```bash
# Auto-generate from model changes
docker-compose exec api alembic revision --autogenerate -m "description"

# Apply
docker-compose exec api alembic upgrade head

# Rollback one
docker-compose exec api alembic downgrade -1
```

### Viewing Celery task logs
```bash
docker-compose logs -f celery_worker
```

---

## 16. How to add a new feature

Follow this exact sequence for any new feature. Never skip steps.

### Step 1 — DB changes (if needed)
1. Add/modify model in `app/models/`
2. Export it in `app/models/__init__.py`
3. Create Alembic migration: `alembic revision --autogenerate -m "feature_name"`
4. Review the generated migration — never blindly trust autogenerate for enum changes
5. Apply: `alembic upgrade head`

### Step 2 — Schemas
1. Add request/response schemas in `app/schemas/`
2. Use `ConfigDict(from_attributes=True)` on all response schemas
3. Never expose `password_hash` in any response schema

### Step 3 — Service
1. Add business logic function in `app/services/`
2. Function signature: `async def my_function(db: AsyncSession, ...) → MyModel`
3. Use `HTTPException` for all error cases with clear messages
4. If the feature changes registration status: go through `registration_service.py`, not ad-hoc

### Step 4 — Router
1. Add route to appropriate router in `app/routers/`
2. Use `require_role(["..."])` dependency for protected routes
3. Call service function — no business logic in the router
4. Return Pydantic schema with `response_model=`

### Step 5 — Register router (if new file)
Add to `app/main.py`:
```python
from app.routers import my_new_router
app.include_router(my_new_router.router)
```

### Step 6 — Frontend (if UI needed)
1. Add API call in relevant page or create new page in `src/pages/`
2. Use `useApi` hook for data fetching
3. Add route in `App.jsx`
4. Wrap with `<ProtectedRoute>` if authentication required

---

## 17. What never to change

These are fixed contracts. Changing them breaks the system.

| What | Why it must not change |
|------|----------------------|
| JWT payload shape `{ sub, role, exp }` | Frontend decodes it in `AuthContext`. Changing field names breaks auth. |
| `registration_status` enum values and order | Status page computes stage number (1–5) from these. Renaming breaks the tracker. |
| `registrations.qr_code_url` stores object key, not full URL | Presigned URLs expire. Storing full URLs would break downloads after 1 hour. |
| Status transitions go through `registration_service.py` | Notifications and timestamps are dispatched there. Bypassing the service skips them. |
| Celery task signatures (`send_email_task`, `send_whatsapp_task`, `generate_certificate_task`) | Called by name from multiple places. Changing signatures requires updating all callers. |
| MinIO object naming: `qr/{id}.png`, `certificates/{id}.pdf` | Existing stored files would become inaccessible if the path changes. |
| `require_role` dependency pattern | All protected routes depend on this. Replacing it breaks authorization everywhere. |
| `event_organizers` ownership check | Organizer isolation depends on this. Removing it creates a security hole. |

---

## 18. Known design decisions and why

### Why volunteer is not a user_role
Volunteer is a per-event assignment, not a permanent identity. A person can be a participant in one marathon and a volunteer in another. If `volunteer` were a role, they'd need two accounts. The `volunteer_assignments` and `volunteer_applications` tables capture this correctly.

### Why QR code encodes registration UUID, not BIB number
BIB numbers are organizer-assigned strings (potentially non-unique across events). The registration UUID is guaranteed unique across the entire platform and is the correct lookup key. The scanner uses the UUID to find the registration, then shows the BIB number to confirm.

### Why certificate URL is stored as object key
Presigned MinIO URLs expire (default 1 hour for QR, 7 days for certificates). Storing the full URL in the DB means it becomes invalid after expiry. Storing the object key means we can generate a fresh presigned URL at any time.

### Why account creation is separate from event registration
One user account can register for multiple events over time. Mixing them would lock users to one event at signup and prevent future registrations without creating a new account. Separation also enables a proper event browser UX.

### Why volunteer applications require approved participant status
Ensures the volunteer is a committed, identity-verified person. Anonymous or rejected registrations cannot volunteer. This is also how real marathon volunteers work — they're almost always participants first.

### Why slot cap is checked twice (at application and at approval)
Race condition: two organizers could approve simultaneously, both passing the cap check, both creating `volunteer_assignments` rows, resulting in one over-cap. The `SELECT FOR UPDATE` at approval time prevents this.

### Why Celery is used instead of FastAPI BackgroundTasks
`BackgroundTasks` in FastAPI runs in the same process. If the API server restarts mid-task, the task is lost. Celery with Redis persistence means tasks survive restarts and can be retried on failure.

### Why organizer accounts use invite-only flow
Public organizer signup would allow anyone to create events on the platform. Admin-controlled invite flow ensures only trusted people can create and manage events, protecting participant data.

---

*Last updated: reflects all changes through Sprint 0 retrofit and Changes 1–5 (auth split, enum refactor, event browse, volunteer application system, frontend overhaul).*