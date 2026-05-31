# Build and Test Summary — Marathon Management Platform Sprint 1

## Quick Start
```bash
cd marathon-api
docker-compose up --build
docker-compose exec api alembic upgrade head
```

## Acceptance Criteria Checklist

| # | Criteria | How to Verify |
|---|----------|---------------|
| AC-1 | docker-compose up --build starts all services | Run command, check all 4 containers are up |
| AC-2 | alembic upgrade head creates all tables | Run migration, check \dt in psql |
| AC-3 | POST /auth/register returns 200 with access_token | curl test in unit-test-instructions.md |
| AC-4 | POST /auth/login with wrong password returns 401 | curl test in unit-test-instructions.md |
| AC-5 | GET /events/{id} with valid UUID returns event JSON | curl test in unit-test-instructions.md |
| AC-6 | GET /events/{id} with invalid UUID returns 404 | curl test in unit-test-instructions.md |
| AC-7 | Protected route without token returns 401 | curl test in unit-test-instructions.md |
| AC-8 | Organizer route called by participant returns 403 | curl test in unit-test-instructions.md |
| AC-9 | /docs shows all routes with correct schemas | Open http://localhost:8000/docs |

## Services
| Service | URL | Credentials |
|---------|-----|-------------|
| API | http://localhost:8000 | — |
| Swagger UI | http://localhost:8000/docs | — |
| PostgreSQL | localhost:5432 | marathon/marathon |
| Redis | localhost:6379 | — |
| MinIO API | http://localhost:9000 | admin/password123 |
| MinIO Console | http://localhost:9001 | admin/password123 |

## Sprint 2 Readiness
- Notification stubs are in place (logger.info calls)
- MinIO client (boto3) is in requirements.txt
- Redis client is in requirements.txt
- Celery is in requirements.txt for async task processing
- SMTP config is in Settings (ready to wire up)
