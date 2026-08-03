import uuid
from datetime import UTC, datetime
from enum import Enum, StrEnum
from typing import Optional

from dateutil.rrule import rrulestr
from pydantic import model_validator, validator
from sqlmodel import Field, Relationship, SQLModel

from app.auth.models import User
from app.core.mixins import IDMixin


class Status(StrEnum):
    """
    Lifecycle status of a task.
    """

    BACKLOG = "backlog"  # not fully defined
    PAUSED = "paused"  # passiv, no action needed
    WAITING = "waiting"  # active, but blocked by external condition
    PLANNED = "planned"  # ready to start
    IN_PROGRESS = "in_progress"  # active, on going
    DONE = "done"  # finished
    CANCELLED = "cancelled"  # abandoned, failure or user decision
    ARCHIVED = "archived"  # hidden from frontend, kept in database


class Task(IDMixin, table=True):
    """
    Task object
    """

    # Define
    title: str = Field(index=True, max_length=255)
    description: str = Field(default="")
    status: Status = Field(default=Status.BACKLOG)

    # Planning
    due_date: datetime | None = None
    start_date: datetime | None = None
    completed_at: datetime | None = None

    # Tracking
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime | None = Field(default=None)

    # Foreign Keys
    user_id: uuid.UUID = Field(foreign_key="user.id")
    parent_id: uuid.UUID | None = Field(default=None, foreign_key="task.id")

    # Autojointure for sub-tasks (Parent / Child)
    parent: Optional[Task] = Relationship(
        back_populates="children",
        sa_relationship_kwargs={"remote_side": "Task.id"},
    )
    children: list[Task] = Relationship(back_populates="parent")
    user: User = Relationship(back_populates="tasks")


class RoutineStatus(str, Enum):
    """
    Lifecycle status of a Routine.
    """

    UNDEFINED = "undefined"  # not fully defined
    ACTIVE = "active"  # running
    INACTIVE = "inactive"  # paused
    ARCHIVED = "archived"  # moved to background


class RecurrencyType(str, Enum):
    """
    Type of Recurrency for Routines
    """

    FIXED_SCHEDULE = "fixed"  # based on calendar
    AFTER_COMPLETED = "relative"  # relative to last completion


class Routine(SQLModel, table=True):
    """
    Routine object, representing an action performed on a cyclic repetition.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    # Define
    title: str = Field(index=True, max_length=255)
    description: str = Field(default="")
    status: RoutineStatus = Field(default=RoutineStatus.UNDEFINED)

    recurrency_type: RecurrencyType = Field(default=RecurrencyType.FIXED_SCHEDULE)

    start_date: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="starting point for recurrency calculation",
    )

    # strategy FIXED_SCHEDULE
    recurrency_rule: str | None = Field(
        default=None,
        max_length=255,
        description="Recurrency rule in RRULE (RFC 5545) format",
    )

    # strategy RELATIVE
    interval_days: int = Field(default=0, gt=-1)

    @validator("recurrency_rule")
    def _rrule_check(cls, rule: str | None) -> str | None:
        """
        Validate `rule` as an RFC 5545 RRULE string.

        Args:
            rule (str | None): the rule to validate; skipped if None.

        Raises:
            ValueError: if `rule` is not a valid RRULE string.

        Returns:
            str | None: the validated rule.
        """
        try:
            rrulestr(rule) if rule is not None else None
        except ValueError:
            raise ValueError("Name cannot be an empty string") from None

        return rule

    @model_validator(mode="after")
    def _check_recurrence_config(self) -> Routine:
        """
        Validate that recurrence fields match the selected `recurrency_type`.

        Raises:
            ValueError: if required fields are missing or forbidden fields are set for the type.

        Returns:
            Routine: self, unchanged.
        """

        if self.recurrency_type == RecurrencyType.FIXED_SCHEDULE:
            if not self.recurrency_rule or not self.start_date:
                raise ValueError(
                    "recurrence_rule et start_date sont requis pour une routine "
                    "de type FIXED_SCHEDULE"
                )
            if self.interval_days is not None:
                raise ValueError(
                    "interval_days ne doit pas être défini pour une routine de type FIXED_SCHEDULE"
                )

        elif self.recurrency_type == RecurrencyType.AFTER_COMPLETED:
            if self.interval_days is None:
                raise ValueError(
                    "interval_days est requis pour une routine de type AFTER_COMPLETION"
                )
            if self.recurrency_rule is not None or self.start_date is not None:
                raise ValueError(
                    "recurrence_rule et start_date ne doivent pas être définis "
                    "pour une routine de type AFTER_COMPLETION"
                )

        return self
