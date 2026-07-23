from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import select

from config import settings
from config.database import SessionDep

from .models import User
from .security import (
    verify_password,
    get_password_hash,
    create_token,
    decode_token,
)


from .schemas import Token, UserResponse
from .deps import get_current_user


auth_router = APIRouter()


@auth_router.post("/login", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: SessionDep,
):
    """
    Endpoint compatible OpenAPI / Swagger UI.
    """

    user = User.get_by_username(session, form_data.username)

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants incorrects",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_token(
        subject=user.username,
        expires_delta=timedelta(minutes=settings.auth.ACCESS_TOKEN_EXPIRE_MINUTES),
        token_type="access",
    )
    refresh_token = create_token(
        subject=user.username,
        expires_delta=timedelta(days=settings.auth.REFRESH_TOKEN_EXPIRE_DAYS),
        token_type="refresh",
    )

    return Token(access_token=access_token, refresh_token=refresh_token)


@auth_router.post("/refresh", response_model=Token)
async def refresh_token(refresh_token: str):
    """
    Renouvelle l'Access Token à partir d'un Refresh Token valide.
    """
    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token invalide"
        )

    username: str = payload.get("sub", "")

    new_access_token = create_token(
        subject=username,
        expires_delta=timedelta(minutes=settings.auth.ACCESS_TOKEN_EXPIRE_MINUTES),
        token_type="access",
    )
    new_refresh_token = create_token(
        subject=username,
        expires_delta=timedelta(days=settings.auth.REFRESH_TOKEN_EXPIRE_DAYS),
        token_type="refresh",
    )

    return Token(access_token=new_access_token, refresh_token=new_refresh_token)


@auth_router.post("/subscribe")
async def subscribe(*args, **kwargs):
    """
    Create a new user and return token.
    """


user_router = APIRouter()


@user_router.get("/profile", response_model=UserResponse)
async def read_users_me(current_user: Annotated[dict, Depends(get_current_user)]):
    """
    Route protégée : nécessite un Bearer Access Token valide.
    """
    return current_user
