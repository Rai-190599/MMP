import enum
import uuid

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class RegistrationStatus(str, enum.Enum):
    registered = "registered"
    approved = "approved"
    participation_confirmed = "participation_confirmed"
    bib_collected = "bib_collected"
    finished_certified = "finished_certified"


class Registration(Base, TimestampMixin):
    __tablename__ = "registrations"
    __table_args__ = (
        UniqueConstraint("event_id", "user_id", name="uq_registration_event_user"),
    )

    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[RegistrationStatus] = mapped_column(
        Enum(RegistrationStatus, name="registration_status", create_type=True),
        nullable=False,
        default=RegistrationStatus.registered,
    )
    distance: Mapped[str | None] = mapped_column(String(20), nullable=True)
    tshirt_size: Mapped[str | None] = mapped_column(String(10), nullable=True)
    emergency_contact: Mapped[str | None] = mapped_column(String(255), nullable=True)
    bib_number: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)
    qr_code_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    finish_time: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    certificate_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    confirmed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    bib_collected_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    event: Mapped["Event"] = relationship("Event", back_populates="registrations")  # noqa: F821
    user: Mapped["User"] = relationship("User", back_populates="registrations")  # noqa: F821
    notifications: Mapped[list["Notification"]] = relationship(  # noqa: F821
        "Notification",
        back_populates="registration",
        lazy="select",
        cascade="all, delete-orphan",
    )
