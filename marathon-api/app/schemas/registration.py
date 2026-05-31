import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class RegistrationCreate(BaseModel):
    event_id: uuid.UUID
    distance: Optional[str] = None
    tshirt_size: Optional[str] = None
    emergency_contact: Optional[str] = None


class EventRegistrationRequest(BaseModel):
    event_id: uuid.UUID
    distance: str
    tshirt_size: str
    emergency_contact: str


class BIBAssignRequest(BaseModel):
    bib_number: Optional[str] = Field(default=None, max_length=20)
    # If omitted, the backend auto-generates: {EVENT_PREFIX}-{sequence}


class FinishTimeRequest(BaseModel):
    finish_time: datetime


# Nested user info embedded in registration responses
class _UserInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: str
    phone: Optional[str] = None


class RegistrationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    event_id: uuid.UUID
    user_id: uuid.UUID
    status: str
    distance: Optional[str] = None
    tshirt_size: Optional[str] = None
    emergency_contact: Optional[str] = None
    bib_number: Optional[str] = None
    qr_code_url: Optional[str] = None
    finish_time: Optional[datetime] = None
    certificate_url: Optional[str] = None
    confirmed_at: Optional[datetime] = None
    bib_collected_at: Optional[datetime] = None
    created_at: datetime
    # Nested user info — populated when the relationship is loaded
    user: Optional[_UserInfo] = None


class StageInfo(BaseModel):
    stage: int
    label: str
    completed: bool
    timestamp: Optional[datetime] = None


class StatusPageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    event_id: uuid.UUID
    user_id: uuid.UUID
    status: str
    distance: Optional[str] = None
    tshirt_size: Optional[str] = None
    emergency_contact: Optional[str] = None
    bib_number: Optional[str] = None
    qr_code_url: Optional[str] = None
    finish_time: Optional[datetime] = None
    certificate_url: Optional[str] = None
    confirmed_at: Optional[datetime] = None
    bib_collected_at: Optional[datetime] = None
    created_at: datetime
    # 5-stage tracker
    current_stage: int
    stages: list[StageInfo]
