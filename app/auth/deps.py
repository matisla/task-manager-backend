from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import select

from .security import decode_token
from .models import User

from config.database import SessionDep


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: SessionDep,
):
    """
    Acquire current user based on the token provided in the header.
    Expect "Authorization: Bearer <token>"

    Args:
        token (str): token to acquire user from

    Raises:
        HTTPException: when not able to acquire the user from token.

    Returns:
        user (...): the acquired user
    """

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token invalide or expired.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # decode the payload
    payload = decode_token(token)
    if not payload:
        raise credentials_exception

    # validate access token and not refresh token
    if payload.get("type") != "access":
        raise credentials_exception

    # get the username for subject
    username: str | None = payload.get("sub")
    if username is None:
        raise credentials_exception

    # get the user from the database
    user = User.get_by_username(session, username)

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(status_code=400, detail="User deactivated")

    return user
