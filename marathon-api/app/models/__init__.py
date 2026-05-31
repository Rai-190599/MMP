# Export all models so Alembic can discover them via Base.metadata
from app.models.base import Base, TimestampMixin
from app.models.event import Event
from app.models.event_organizer import EventOrganizer
from app.models.notification import Notification, NotificationChannel, NotificationTriggerType
from app.models.organizer_invite import OrganizerInvite
from app.models.registration import Registration, RegistrationStatus
from app.models.task import Task, TaskCategory, TaskStatus
from app.models.user import User, UserRole
from app.models.volunteer_application import VolunteerApplication
from app.models.volunteer_assignment import VolunteerAssignment, VolunteerRoleType

__all__ = [
    "Base",
    "TimestampMixin",
    "User",
    "UserRole",
    "Event",
    "EventOrganizer",
    "OrganizerInvite",
    "Registration",
    "RegistrationStatus",
    "Notification",
    "NotificationChannel",
    "NotificationTriggerType",
    "Task",
    "TaskCategory",
    "TaskStatus",
    "VolunteerApplication",
    "VolunteerAssignment",
    "VolunteerRoleType",
]
