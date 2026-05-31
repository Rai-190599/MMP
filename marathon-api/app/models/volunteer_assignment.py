import enum
import uuid

from sqlalchemy import Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class VolunteerRoleType(str, enum.Enum):
    registration_desk = "registration_desk"
    finish_line = "finish_line"
    general = "general"


class VolunteerAssignment(Base, TimestampMixin):
    __tablename__ = "volunteer_assignments"
    __table_args__ = (
        UniqueConstraint("event_id", "user_id", name="uq_volunteer_assignment_event_user"),
    )

    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role_type: Mapped[VolunteerRoleType] = mapped_column(
        Enum(VolunteerRoleType, name="volunteer_role_type", create_type=True),
        nullable=False,
    )
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Relationships
    event: Mapped["Event"] = relationship("Event", back_populates="volunteer_assignments")  # noqa: F821
    user: Mapped["User"] = relationship("User", back_populates="volunteer_assignments")  # noqa: F821
