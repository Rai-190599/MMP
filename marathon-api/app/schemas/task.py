import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ChecklistItem(BaseModel):
    item: str
    done: bool = False


class TaskCreate(BaseModel):
    event_id: uuid.UUID
    title: str
    category: str
    assignee_id: Optional[uuid.UUID] = None
    deadline: Optional[date] = None
    checklist: list[ChecklistItem] = []


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None
    assignee_id: Optional[uuid.UUID] = None
    deadline: Optional[date] = None
    checklist: Optional[list[ChecklistItem]] = None
    status: Optional[str] = None


class ChecklistItemUpdate(BaseModel):
    index: int
    done: bool


class _AssigneeInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    event_id: uuid.UUID
    title: str
    category: str
    status: str
    deadline: Optional[date] = None
    checklist: list[ChecklistItem] = []
    assignee_id: Optional[uuid.UUID] = None
    assignee: Optional[_AssigneeInfo] = None
    created_at: Optional[datetime] = None
