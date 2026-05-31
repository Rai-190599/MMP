import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class VolunteerApplication(Base):
    """
    Tracks a user's application to volunteer at a specific event.

    desired_role: 'registration_desk' | 'finish_line' | 'general'
    status:       'pending' | 'approved' | 'rejected'
    """

    __tablename__ = "volunteer_applications"
    __table_args__ = (
        UniqueConstraint("event_id", "user_id", name="uq_volunteer_application_event_user"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default="gen_random_uuid()",
        nullable=False,
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    desired_role: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="pending"
    )
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    event: Mapped["Event"] = relationship("Event", back_populates="volunteer_applications")  # noqa: F821
    user: Mapped["User"] = relationship("User", back_populates="volunteer_applications")  # noqa: F821
