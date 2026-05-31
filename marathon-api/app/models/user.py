import enum

from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class UserRole(str, enum.Enum):
    participant = "participant"
    organizer = "organizer"
    admin = "admin"


class User(Base, TimestampMixin):
    __tablename__ = "users"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name='user_role', create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # Relationships
    registrations: Mapped[list["Registration"]] = relationship(  # noqa: F821
        "Registration", back_populates="user", lazy="select"
    )
    assigned_tasks: Mapped[list["Task"]] = relationship(  # noqa: F821
        "Task", back_populates="assignee", lazy="select"
    )
    volunteer_assignments: Mapped[list["VolunteerAssignment"]] = relationship(  # noqa: F821
        "VolunteerAssignment", back_populates="user", lazy="select"
    )
    volunteer_applications: Mapped[list["VolunteerApplication"]] = relationship(  # noqa: F821
        "VolunteerApplication", back_populates="user", lazy="select"
    )
