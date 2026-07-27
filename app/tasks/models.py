import uuid
from datetime import UTC, datetime
from enum import Enum

from auth.models import User
from sqlmodel import Column, DateTime, Field, Relationship, SQLModel


class Status(str, Enum):
    BACKLOG = "backlog"  # not fully defined
    PAUSED = "paused"  # passiv, no action needed
    WAITING = "waiting"  # active, but blocked by external condition
    PLANNED = "planned"  # ready to start
    IN_PROGRESS = "in_progress"  # active, on going
    DONE = "done"  # finished


class Task(SQLModel, table=True):
    """
    Task object
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    # Define
    title: str = Field(index=True, max_length=255)
    description: str = Field(default="")
    status: Status = Field(default=Status.BACKLOG)

    # Planning
    due_date: datetime | None = None
    start_date: datetime | None = None
    completed_at: datetime | None = None

    # Tracking
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True), default_factory=lambda: datetime.now(UTC)
        )
    )
    updated_at: datetime | None = Field(
        sa_column=Column(DateTime(timezone=True)), default=None
    )

    # Foreign Keys
    user_id: uuid.UUID = Field(foreign_key="user.id")
    parent_id: uuid.UUID | None = Field(default=None, foreign_key="task.id")

    # Autojointure for sub-tasks (Parent / Child)
    parent: Task | None = Relationship(
        back_populates="children", sa_relationship_kwargs={"remote_side": "Task.id"}
    )
    children: list[Task] = Relationship(back_populates="parent")
    user: User = Relationship(back_populates="tasks")
