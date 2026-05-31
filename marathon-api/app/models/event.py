from sqlalchemy import Boolean, Date, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Event(Base, TimestampMixin):
    __tablename__ = "events"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    event_date: Mapped[Date] = mapped_column(Date, nullable=False)
    location: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # JSONB fields — e.g. distances: ["5K", "10K", "21K"]
    distances: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    sponsor_tiers: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    faq: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    volunteer_slot_caps: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        server_default='{"registration_desk": 5, "finish_line": 3, "general": 10}',
    )
    # List of MinIO object names for event banner images
    # e.g. ["banners/event-id/1.jpg", "banners/event-id/2.jpg"]
    banner_images: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
        server_default="'[]'::jsonb",
    )

    # Relationships
    registrations: Mapped[list["Registration"]] = relationship(  # noqa: F821
        "Registration", back_populates="event", lazy="select"
    )
    tasks: Mapped[list["Task"]] = relationship(  # noqa: F821
        "Task", back_populates="event", lazy="select"
    )
    volunteer_assignments: Mapped[list["VolunteerAssignment"]] = relationship(  # noqa: F821
        "VolunteerAssignment", back_populates="event", lazy="select"
    )
    volunteer_applications: Mapped[list["VolunteerApplication"]] = relationship(  # noqa: F821
        "VolunteerApplication", back_populates="event", lazy="select"
    )
