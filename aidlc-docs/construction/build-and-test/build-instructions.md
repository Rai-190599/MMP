# Build Instructions — Marathon Management Platform Sprint 1

## Prerequisites
- Docker Desktop (or Docker Engine + Docker Compose v2)
- Python 3.11 (for local development / running migrations outside Docker)

## Step 1: Clone / Navigate to Project Root
```bash
cd marathon-api
```

## Step 2: Copy Environment File
```bash
cp .env.example .env
# The .env file is already pre-configured for Docker Compose (uses service hostnames)
# Edit SECRET_KEY for any non-dev environment
```

## Step 3: Build and Start All Services
```bash
docker-compose up --build
```

Expected output:
- `marathon_postgres` starts and passes healthcheck
- `marathon_redis` starts and passes healthcheck
- `marathon_minio` starts
- `marathon_api` starts after postgres is healthy
- API available at http://localhost:8000

## Step 4: Run Database Migrations

In a separate terminal (while Docker Compose is running):
```bash
# Option A: Run inside the api container
docker-compose exec api alembic upgrade head

# Option B: Run locally (requires local Python env with requirements installed)
# First set DATABASE_URL to use localhost:5432
DATABASE_URL=postgresql+asyncpg://marathon:marathon@localhost:5432/marathon_db alembic upgrade head
```

Expected output:
```
INFO  [alembic.runtime.migration] Running upgrade  -> 001, 001 initial schema
```

## Step 5: Verify API is Running
```bash
curl http://localhost:8000/health
# Expected: {"status": "ok"}

# Open Swagger UI
open http://localhost:8000/docs
```

## Stopping Services
```bash
docker-compose down          # Stop and remove containers
docker-compose down -v       # Also remove volumes (wipes database)
```

## Local Development (without Docker)

```bash
# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set local DATABASE_URL (postgres must be running locally or via Docker)
export DATABASE_URL=postgresql+asyncpg://marathon:marathon@localhost:5432/marathon_db
export SECRET_KEY=dev-secret-key

# Run migrations
alembic upgrade head

# Start API
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
