from datetime import UTC, datetime, timedelta

from config import get_settings
from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session

from .models import User
from .schemas import Token, UserCreate
from .security import create_token, decode_token, get_password_hash, verify_password


class UserService:

    @classmethod
    def create(cls, session: Session, data: UserCreate) -> User:
        """
        Create a User based on provided data.

        Args:
            session (Session): session to communicate with the database.
            data (UserCreate): data to use to create the user.

        Raise:
            HTTPException: error if user or email already exist in database.


        Returns:
            (User): return the created user.

        """

        exception = HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or Email already exist",
        )

        # Check if User is already existing
        exist_user = User.get_by(session, "username", data.username)
        if exist_user:
            raise exception

        exist_user = User.get_by(session, "email", data.email)
        if exist_user:
            raise exception

        # Hash password

        hashed_pwd = get_password_hash(data.password)

        # Create user

        db_user = User(
            username=data.username,
            firstname=data.firstname,
            lastname=data.lastname,
            email=data.email,
            hashed_password=hashed_pwd,
            created_at=datetime.now(UTC),
        )

        # publish to database

        session.add(db_user)
        session.commit()
        session.refresh(db_user)

        return db_user


class TokenService:

    @classmethod
    def login(cls, session: Session, data: OAuth2PasswordRequestForm) -> Token:

        settings = get_settings()
        user = User.get_by(session, "username", data.username)

        # verify user password
        if not user or not verify_password(data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Identifiants incorrects",
                headers={"WWW-Authenticate": "Bearer"},
            )

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

        settings = get_settings()
        payload = decode_token(refresh_token)

        if not payload or payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token invalide",
            )

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
