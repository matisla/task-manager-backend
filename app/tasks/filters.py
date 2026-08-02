import uuid

from sqlmodel import SQLModel

from .models import Status


class TaskFilter(SQLModel):
    """
    Equality filters accepted when listing tasks.
    """

    status: Status | None = None
    user_id: uuid.UUID | None = None
    parent_id: uuid.UUID | None = None
