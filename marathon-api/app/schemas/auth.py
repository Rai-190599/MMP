import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    password: str
    role: str  # "participant" or "organizer"
    # Participant-only optional fields
    distance: Optional[str] = None
    tshirt_size: Optional[str] = None
    emergency_contact: Optional[str] = None
    event_id: Optional[uuid.UUID] = None

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        allowed = {"participant", "organizer"}
        if v not in allowed:
            raise ValueError(f"role must be one of: {', '.join(allowed)}")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: str
    phone: Optional[str] = None
    role: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class SignupRequest(BaseModel):
    name: str = Field(..., min_length=3)
    email: EmailStr
    phone: str = Field(..., min_length=10)
    password: str = Field(..., min_length=8)


class SignupResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
