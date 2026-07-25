from datetime import timedelta
from typing import Annotated

from config import settings
from config.database import SessionDep
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from .deps import get_current_user
from .models import User
from .schemas import Token, UserResponse
from .security import create_token, decode_token, verify_password

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


@auth_router.post("/subscribe")
async def subscribe(*args, **kwargs):
    """
    Create a new user and return token.
    """


user_router = APIRouter()


@user_router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: Annotated[dict, Depends(get_current_user)]):
    """
    Route protégée : nécessite un Bearer Access Token valide.
    """
    return current_user
