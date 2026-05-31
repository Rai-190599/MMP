from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.dependencies import get_current_user, require_role
from app.models.user import User
from app.routers import admin, auth, certificates, event_mgmt, events, notifications, organizer, registrations, tasks, volunteer_apply, volunteers

app = FastAPI(
    title="Marathon Management Platform API",
    description="Backend API for the Marathon Management Platform — Sprints 1-4",
    version="4.0.0",
)

# CORS — allow frontend dev server and any localhost port
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup() -> None:
    """Ensure MinIO bucket exists and public-read policies are set on every startup."""
    import json
    import logging
    logger = logging.getLogger(__name__)

    from app.services import storage_service
    from app.services.storage_service import BUCKET, _s3

    try:
        storage_service.ensure_bucket_exists()
    except Exception as exc:
        logger.error("MinIO bucket check failed: %s", exc)
        return

    # Set bucket policy so qr/ and banners/ prefixes are publicly readable.
    # This uses the S3 bucket policy API — persisted by MinIO, survives restarts.
    public_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"AWS": ["*"]},
                "Action": ["s3:GetObject"],
                "Resource": [
                    f"arn:aws:s3:::{BUCKET}/qr/*",
                    f"arn:aws:s3:::{BUCKET}/banners/*",
                ],
            }
        ],
    }
    try:
        _s3.put_bucket_policy(
            Bucket=BUCKET,
            Policy=json.dumps(public_policy),
        )
        logger.info("MinIO public policy set for qr/ and banners/ prefixes.")
    except Exception as exc:
        logger.warning("Could not set MinIO bucket policy (non-fatal): %s", exc)


# Include routers
app.include_router(auth.router)
app.include_router(events.router)
app.include_router(registrations.router)
app.include_router(organizer.router)
app.include_router(volunteers.router)
app.include_router(volunteer_apply.router)
app.include_router(certificates.router)
app.include_router(tasks.router)
app.include_router(notifications.router)
app.include_router(admin.router)
app.include_router(event_mgmt.router)


@app.get("/health", tags=["health"])
async def health_check() -> dict:
    """Simple health check endpoint."""
    return {"status": "ok"}


@app.get("/me", tags=["auth"])
async def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Protected route — returns current user info. Requires valid JWT (AC-7)."""
    return {"id": str(current_user.id), "email": current_user.email, "role": current_user.role.value}


@app.get("/organizer-only", tags=["auth"])
async def organizer_only(
    current_user: Annotated[User, Depends(require_role(["organizer"]))],
) -> dict:
    """Organizer-only route — returns 403 for non-organizers (AC-8)."""
    return {"message": "Welcome, organizer!"}
