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
    def get_by(cls, session: Session, attribute: str, value: str) -> User | None:
        """
        Get the user by an attribute

        Args:
            session (Session): session used to access the database
            attribute (str): attribute to use to select the User
            username (str): value to use to select the User

        Returns:
            User | None: the User object or None if not found.
        """

        statement = None

        match attribute:
            case "username":
                statement = select(User).where(User.username == value)
            case "email":
                statement = select(User).where(User.email == value)
            case _:
                raise AttributeError("attribute shall be 'username' or 'email'")

        user: User | None = session.exec(statement).first()
        return user
