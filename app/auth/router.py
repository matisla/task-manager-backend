from typing import Annotated

from database import SessionDep
from fastapi import APIRouter, Depends, Form, status
from fastapi.security import OAuth2PasswordRequestForm

from .deps import currentUserDep
from .schemas import Token, UserCreate, UserResponse
from .services import TokenService, UserService

auth_router = APIRouter()


@auth_router.post("/login", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: SessionDep,
):
    """
    Endpoint compatible OpenAPI / Swagger UI.
    """

    return TokenService.login(session, form_data)


@auth_router.post("/refresh", response_model=Token)
async def refresh_token(refresh_token: str):
    """
    Refresh access token based on `refresh_token`.
    """

    return TokenService.refresh_token(refresh_token)


@auth_router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=UserResponse,
)
async def register(
    user_form: Annotated[UserCreate, Form()],
    session: SessionDep,
):
    """
    Create a new user and return token.
    """

    return UserService.create(session, user_form)


user_router = APIRouter()


@user_router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: currentUserDep):
    """
    Route protégée : nécessite un Bearer Access Token valide.
    """
    return current_user
