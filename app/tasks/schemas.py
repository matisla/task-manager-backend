import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class TaskBase(BaseModel):
    """
    Fields shared by every task schema.
    """

    title: str = Field(max_length=255)
    description: str | None = Field(default="")


class TaskCreate(TaskBase):
    """
    Schema for creating a new task.
    """

    start_date: datetime | None = Field(default=None)
    due_date: datetime | None = Field(default=None)
    parent_id: uuid.UUID | None = Field(default=None)


class TaskRead(TaskBase):
    """
    Schema for exposing a task through the API.
    """

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime | None

    start_date: datetime | None
    due_date: datetime | None

    parent_id: uuid.UUID | None = Field(default=None)
    user_id: uuid.UUID
