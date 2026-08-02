import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, Session, SQLModel, select

if TYPE_CHECKING:
    from tasks.models import Task


class User(SQLModel, table=True):
   """
    User model for the database
    """
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    firstname: str | None = Field(max_length=64, default=None)
    lastname: str | None = Field(max_length=64, default=None)
    username: str = Field(index=True, max_length=64)
    email: str = Field(unique=True, max_length=255)
    hashed_password: str = Field(max_length=255)
    created_at: datetime | None = None
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)

    tasks: list["Task"] = Relationship(back_populates="user")

