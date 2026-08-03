from datetime import UTC, datetime, timedelta

from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import BadRequestError, UnauthorizedError

from .models import User
from .repository import UserRepository
from .schemas import Token, UserCreate
from .security import create_token, decode_token, get_password_hash, verify_password


class UserService:
    """
    Service handling user creation.
    """

    @classmethod
    async def create(cls, session: AsyncSession, data: UserCreate) -> User:
        """
        Create a User based on provided data.

        Args:
            session (AsyncSession): session to communicate with the database.
            data (UserCreate): data to use to create the user.

        Raises:
            BadRequestError: if the username or email already exists in database.

        Returns:
            User: the created user.
        """

        exception = BadRequestError("Username or Email already exist")
        repository = UserRepository(session)

        # Check if User is already existing
        exist_user = await repository.get_by("username", data.username)
        if exist_user:
            raise exception

        exist_user = await repository.get_by("email", data.email)
        if exist_user:
            raise exception

        # Hash password

        hashed_pwd = get_password_hash(data.password)

        # Create user

        user = await repository.create(
            username=data.username,
            firstname=data.firstname,
            lastname=data.lastname,
            email=data.email,
            hashed_password=hashed_pwd,
            created_at=datetime.now(UTC),
        )

        return user


class TokenService:
    """
    Service handling access and refresh token issuance.
    """

    @classmethod
    async def login(cls, session: AsyncSession, data: OAuth2PasswordRequestForm) -> Token:
        """
        Authenticate a user and issue a new access and refresh token pair.

        Args:
            session (AsyncSession): session used to access the database.
            data (OAuth2PasswordRequestForm): the submitted username and password.

        Raises:
            UnauthorizedError: if the credentials are invalid.

        Returns:
            Token: the issued access and refresh tokens.
        """

        settings = get_settings()
        user = await UserRepository(session).get_by("username", data.username)

        # verify user password
        if not user or not verify_password(data.password, user.hashed_password):
            raise UnauthorizedError("Identifiants incorrects")

        access_token = create_token(
            subject=str(user.id),
            expires_delta=timedelta(minutes=settings.auth.ACCESS_TOKEN_EXPIRE_MINUTES),
            token_type="access",
        )
        refresh_token = create_token(
            subject=str(user.id),
            expires_delta=timedelta(days=settings.auth.REFRESH_TOKEN_EXPIRE_DAYS),
            token_type="refresh",
        )

        return Token(access_token=access_token, refresh_token=refresh_token)

    @classmethod
    def refresh_token(cls, refresh_token: str) -> Token:
        """
        Issue a new access and refresh token pair from a valid refresh token.

        No database access is needed here (pure JWT decode/encode), so this method stays
        synchronous.

        Args:
            refresh_token (str): the refresh token to exchange.

        Raises:
            UnauthorizedError: if the refresh token is invalid, expired, or not of type "refresh".

        Returns:
            Token: the newly issued access and refresh tokens.
        """

        settings = get_settings()
        payload = decode_token(refresh_token)

        if not payload or payload.get("type") != "refresh":
            raise UnauthorizedError("Refresh token invalide")

        user_id: str = payload.get("sub", "")

        new_access_token = create_token(
            subject=user_id,
            expires_delta=timedelta(minutes=settings.auth.ACCESS_TOKEN_EXPIRE_MINUTES),
            token_type="access",
        )
        new_refresh_token = create_token(
            subject=user_id,
            expires_delta=timedelta(days=settings.auth.REFRESH_TOKEN_EXPIRE_DAYS),
            token_type="refresh",
        )

        return Token(access_token=new_access_token, refresh_token=new_refresh_token)
