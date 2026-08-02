from core.repository import DefaultRepository
from sqlmodel import Session, select

from .models import User


class UserRepository(DefaultRepository):
    """
    Repository of the model User, used to interface the DB.
    """

    model: User

    def __init__(self, db: Session):
        self.db = db

    def create(self, *args, **kwargs):

        user = User(*args, **kwargs)

        # publish to database

        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        return user

    def get_by(self, attribute: str, value: str) -> User | None:
        """
        Get the user by an attribute.

        Args:
            session (Session): session used to access the database.
            attribute (str): attribute to use to select the User, either "username" or "email".
            value (str): value to use to select the User.

        Raises:
            AttributeError: if `attribute` is neither "username" nor "email".

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

        user: User | None = self.db.exec(statement).first()

        return user
