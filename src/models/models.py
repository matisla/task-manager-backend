from datetime import datetime, timezone
from typing import Optional
from enum import Enum

from settings.database import DATABASE_URL
from sqlmodel import SQLModel, Field, Relationship, Column, DateTime

# ------------------------------------------------
# TASK
# ------------------------------------------------


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

    id: Optional[int] = Field(default=None, primary_key=True)

    # Define
    title: str = Field(index=True, max_length=256)
    description: Optional[str] = None
    status: Status = Field(default=Status.BACKLOG)

    # Planning
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Tracking
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
        )
    )
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
        )
    )

    # Foreign Keys
    project_id: Optional[int] = Field(default=None, foreign_key="project.id")
    routine_id: Optional[int] = Field(default=None, foreign_key="routine.id")
    parent_id: Optional[int] = Field(default=None, foreign_key="task.id")

    # Relations ORM

    # Autojointure for sub-tasks (Parent / Enfants)
    parent: Optional["Task"] = Relationship(
        back_populates="subtasks", sa_relationship_kwargs={"remote_side": "Task.id"}
    )
    subtasks: List["Task"] = Relationship(back_populates="parent")


