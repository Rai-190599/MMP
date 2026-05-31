import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.notification import NotificationChannel, NotificationTriggerType
from app.models.registration import RegistrationStatus


class BroadcastRequest(BaseModel):
    event_id: uuid.UUID
    channel: NotificationChannel
    subject: str = ""          # used for email only
    message: str
    filter_status: Optional[RegistrationStatus] = None


class NotificationLogOut(BaseModel):
    id: uuid.UUID
    registration_id: uuid.UUID
    channel: str
    trigger_type: str
    content: Optional[str]
    sent: bool
    sent_at: Optional[datetime]
    created_at: Optional[datetime]
    # Joined from user via registration
    recipient_name: Optional[str] = None
    recipient_email: Optional[str] = None

    class Config:
        from_attributes = True
