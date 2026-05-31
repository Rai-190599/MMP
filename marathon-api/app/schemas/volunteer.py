import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class VolunteerApplyRequest(BaseModel):
    event_id: uuid.UUID
    desired_role: Literal["registration_desk", "finish_line", "general"]
    note: Optional[str] = Field(default=None, max_length=200)


class VolunteerApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    event_id: uuid.UUID
    user_id: uuid.UUID
    desired_role: str
    status: str
    note: Optional[str] = None
    applied_at: datetime
    reviewed_at: Optional[datetime] = None
    # Joined fields — populated manually in the router
    user_name: str
    user_email: str
    slots_remaining: int


class VolunteerReviewRequest(BaseModel):
    status: Literal["approved", "rejected"]


class _SlotInfo(BaseModel):
    role: str
    cap: int
    filled: int
    remaining: int
    is_open: bool  # remaining > 0


class VolunteerSlotsOut(BaseModel):
    event_id: uuid.UUID
    slots: list[_SlotInfo]
