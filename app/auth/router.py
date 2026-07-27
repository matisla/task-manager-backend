from datetime import UTC, datetime, timedelta
from typing import Annotated

from config import get_settings
from database import SessionDep
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from .deps import get_current_user
from .models import User
from .schemas import Token, UserCreate, UserResponse
from .security import create_token, decode_token, get_password_hash, verify_password

auth_router = APIRouter()


@auth_router.post("/login", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: SessionDep,
):
    """
    Endpoint compatible OpenAPI / Swagger UI.
    """

    settings = get_settings()
    user = User.get_by(session, "username", form_data.username)

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
    settings = get_settings()

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


@auth_router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    user_form: UserCreate,
    session: SessionDep,
):
    """
    Create a new user and return token.
    """
    exception = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Username or Email already exist",
    )

    exist_user = User.get_by(session, "username", user_form.username)
    if exist_user:
        raise exception

    exist_user = User.get_by(session, "email", user_form.email)
    if exist_user:
        raise exception

    hashed_pwd = get_password_hash(user_form.password)

    db_user = User(
        username=user_form.username,
        firstname=user_form.firstname,
        lastname=user_form.lastname,
        email=user_form.email,
        hashed_password=hashed_pwd,
        created_at=datetime.now(UTC),
    )

    session.add(db_user)
    session.commit()
    session.refresh(db_user)

    return db_user


user_router = APIRouter()


@user_router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: Annotated[dict, Depends(get_current_user)]):
    """
    Route protégée : nécessite un Bearer Access Token valide.
    """
    return current_user
