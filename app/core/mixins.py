import uuid
from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class IDMixin(SQLModel):
    """
    Mixin adding a UUID primary key.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)


class TimestampMixin(SQLModel):
    """
    Mixin adding creation and last-update timestamps.
    """

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime | None = Field(
        default=None,
        sa_column_kwargs={"onupdate": lambda: datetime.now(UTC)},
    )
