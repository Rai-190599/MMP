import enum
import uuid

from sqlalchemy import Date, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class TaskCategory(str, enum.Enum):
    sponsors = "sponsors"
    tshirt = "tshirt"
    bib = "bib"
    volunteers = "volunteers"
    logistics = "logistics"


class TaskStatus(str, enum.Enum):
    todo = "todo"
    in_progress = "in_progress"
    done = "done"


class Task(Base, TimestampMixin):
    __tablename__ = "tasks"

    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False
    )
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    category: Mapped[TaskCategory] = mapped_column(
        Enum(TaskCategory, name="task_category", create_type=True),
        nullable=False,
    )
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, name="task_status", create_type=True),
        nullable=False,
        default=TaskStatus.todo,
    )
    deadline: Mapped[Date | None] = mapped_column(Date, nullable=True)
    checklist: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    # Relationships
    event: Mapped["Event"] = relationship("Event", back_populates="tasks")  # noqa: F821
    assignee: Mapped["User | None"] = relationship("User", back_populates="assigned_tasks")  # noqa: F821
