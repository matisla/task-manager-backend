from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship

from app.core.mixins import IDMixin, TimestampMixin

if TYPE_CHECKING:
    from tasks.models import Task


class User(IDMixin, TimestampMixin, table=True):
    """
    User model for the database
    """

    firstname: str | None = Field(max_length=64, default=None)
    lastname: str | None = Field(max_length=64, default=None)
    username: str = Field(index=True, max_length=64)
    email: str = Field(unique=True, max_length=255)
    hashed_password: str = Field(max_length=255)
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)

    tasks: list["Task"] = Relationship(back_populates="user")
