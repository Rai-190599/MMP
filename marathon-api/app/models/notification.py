import enum
import uuid

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class NotificationChannel(str, enum.Enum):
    email = "email"
    sms = "sms"
    whatsapp = "whatsapp"


class NotificationTriggerType(str, enum.Enum):
    status_change = "status_change"
    manual_broadcast = "manual_broadcast"


class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"

    registration_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("registrations.id", ondelete="CASCADE"),
        nullable=False,
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(NotificationChannel, name="notification_channel", create_type=True),
        nullable=False,
    )
    trigger_type: Mapped[NotificationTriggerType] = mapped_column(
        Enum(NotificationTriggerType, name="notification_trigger_type", create_type=True),
        nullable=False,
    )
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sent_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    registration: Mapped["Registration"] = relationship(  # noqa: F821
        "Registration", back_populates="notifications"
    )
