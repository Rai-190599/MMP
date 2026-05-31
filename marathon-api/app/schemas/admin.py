import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator


class InviteCreateRequest(BaseModel):
    email: EmailStr
    name: str


class InviteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    token: uuid.UUID
    invited_by: uuid.UUID | None
    accepted: bool
    expires_at: datetime
    created_at: datetime
    status: Literal["pending", "accepted", "expired"] = "pending"


class AcceptInviteRequest(BaseModel):
    token: uuid.UUID
    name: str
    password: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("password must be at least 8 characters")
        return v


class UserAdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: str
    role: str
    created_at: datetime
