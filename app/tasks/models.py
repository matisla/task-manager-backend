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
    project: Optional[Project] = Relationship(back_populates="tasks")
    routine: Optional[Routine] = Relationship(back_populates="generated_tasks")
    tags: List[Tag] = Relationship(back_populates="tasks", link_model=TaskTagLink)

    # Autojointure for sub-tasks (Parent / Enfants)
    parent: Optional["Task"] = Relationship(
        back_populates="subtasks", sa_relationship_kwargs={"remote_side": "Task.id"}
    )
    subtasks: List["Task"] = Relationship(back_populates="parent")


# ------------------------------------------------
# ROUTINE
# ------------------------------------------------


class RecurrenceType(str, Enum):
    CALENDAR = "calendar"  # every ...
    RELATIVE = "relative"  # every ... since last achivement


class Recurrence:
    """
    Represent the recurrency that could be configured.
    """

    week_mask: int = 0  # mask: 2^7
    month_mask: int = 0  # mask: 2^12
    month_days: list[int] = []  # days of the month

    def set_week_day(self, *values: int):
        """
        set the day of the week.

        Args:
            values (tuple[int]): the day or days of the week to set.
                set all days, if no value provided.

        Monday: 0
        ...
        Sunday: 6
        """
        if not values:
            self.week_mask = 0b1111111
            return

        for value in values:
            if isinstance(value, int):
                ValueError(f"'{value}' shall be a int.")
            elif 0 <= value <= 6:
                self.week_mask |= 1 << value
            else:
                ValueError(f"'{value}' is not a valid week day.")

    def reset_week_day(self):
        self.week_mask = 0

    def serial(self):

        week_day = "*"
        if self.week_mask != 0b1111111:
            week_day = ",".join([str(i) for i in range(7) if (self.week_mask >> i) & 1])

        month = "*"
        if self.month_mask != 0b111111111111:
            month = ",".join([str(i) for i in range(12) if (self.week_mask >> i) & 1])

        month_days = ",".join([str(i) for i in self.month_days])

        return f"{month_days} {month} {week_day}"


class Routine(SQLModel, table=True):
    """
    Routine is something with a cycle time, and no end.
    It produce a Task based on the cycle time.
    """

    id: Optional[int] = Field(default=None, primary_key=True)

    # Define
    title: str = Field(index=True, max_length=256)
    description: Optional[str] = None

    recurrence_type: RecurrenceType = Field(default=RecurrenceType.CALENDAR)
    frequency_interval: int = Field(default=1)
    frequency_unit: FrequencyUnit = Field(default=FrequencyUnit.WEEK)

    is_active: bool = Field(default=True)
    last_completed_at: Optional[datetime] = None

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

    # Relations
    generated_tasks: List["Task"] = Relationship(back_populates="routine")
    tags: List[Tag] = Relationship(back_populates="routines", link_model=RoutineTagLink)
