import uuid
from datetime import datetime

from sqlmodel import Field, Session, SQLModel, select


class User(SQLModel, table=True):
    """
    User model for the database
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    firstname: str = Field(max_length=64)
    lastname: str = Field(max_length=64)
    username: str = Field(index=True, max_length=64)
    email: str = Field(unique=True, max_length=255)
    hashed_password: str = Field(max_length=255)
    created_at: datetime | None = None
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)

    @classmethod
    def get_by_username(cls, session: Session, username: str) -> "User | None":
        """
        Get the user by his username

        Args:
            session (Session): session used to access the database
            username (str): username to use to select the User

        Returns:
            User | None: the User object or None if not found.
        """

        statement = select(User).where(User.username == username)
        user: User | None = session.exec(statement).first()

        return user
