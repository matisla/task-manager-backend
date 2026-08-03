from sqlmodel import select

from app.core.repository import DefaultRepository

from .models import User


class UserRepository(DefaultRepository[User]):
    """
    Repository for the User model, adds lookup by username/email.
    """

    model = User

    async def get_by(self, attribute: str, value: str) -> User | None:
        """
        Get the user by an attribute.

        Args:
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

        result = await self.session.exec(statement)
        user: User | None = result.first()

        return user
