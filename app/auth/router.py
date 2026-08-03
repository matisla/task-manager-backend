from typing import Annotated

from fastapi import APIRouter, Depends, Form, status
from fastapi.security import OAuth2PasswordRequestForm

from app.db.deps import SessionDep

from .deps import currentUserDep
from .schemas import Token, UserCreate, UserResponse
from .services import TokenService, UserService

auth_router = APIRouter(prefix="/auth", tags=["Auth"])


@auth_router.post("/login", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: SessionDep,
):
    """
    Endpoint compatible OpenAPI / Swagger UI.
    Authenticate a user and return an access and refresh token pair.

    Args:
        form_data (OAuth2PasswordRequestForm): username and password submitted via form.
        session (Session): session used to access the database.

    Returns:
        Token: the issued access and refresh tokens.
    """

    return await TokenService.login(session, form_data)


@auth_router.post("/refresh", response_model=Token)
async def refresh_token(refresh_token: str):
    """
    Refresh access token based on `refresh_token`.

    Args:
        refresh_token (str): the refresh token to exchange for a new token pair.

    Returns:
        Token: the newly issued access and refresh tokens.
    """

    return TokenService.refresh_token(refresh_token)  # sync: no DB/session access


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

    Args:
        user_form (UserCreate): data to use to create the user.
        session (Session): session used to access the database.

    Returns:
        UserResponse: the created user.
    """

    return await UserService.create(session, user_form)


user_router = APIRouter(prefix="/users", tags=["Users"])


@user_router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: currentUserDep):
    """
    Protected route: requires a valid Bearer access token.

    Args:
        current_user (User): the user resolved from the access token.

    Returns:
        UserResponse: the current authenticated user.
    """
    return current_user
