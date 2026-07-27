import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class TaskBase(BaseModel):
    title: str = Field(max_length=256)


class TaskCreate(BaseModel):

    title: str = Field(max_length=255)
    description: str | None = Field(default="")

    start_date: datetime | None = Field(default=None)
    due_date: datetime | None = Field(default=None)
    parent_id: uuid.UUID | None = Field(default=None)


class TaskRead(BaseModel):
    id: uuid.UUID

    title: str
    description: str
    created_at: datetime

    start_date: datetime | None
    due_date: datetime | None

    parent: uuid.UUID | None = Field(default=None)
