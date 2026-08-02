import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    """
    Fields shared by every user schema.
    """

    username: str = Field(min_length=3, max_length=63, examples=["johndoe"])
    firstname: str | None = Field(min_length=1, max_length=64, default=None, examples=["John"])
    lastname: str | None = Field(min_length=1, max_length=64, default=None, examples=["Doe"])
    email: EmailStr = Field(examples=["johndoe@example.com"])


class UserCreate(UserBase):
    """
    Schema for creating a new user.
    """

    password: str = Field(min_length=8, examples=["SecuredPassword_123!"])


class UserLogin(BaseModel):
    """
    Schema for login a user
    """

    username: str
    password: str


class UserResponse(UserBase):
    """
    Schema for exposing a user through the API.
    """

    id: uuid.UUID
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    """
    Schema for an access and refresh token pair.
    """

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """
    Schema for the payload encoded in a JWT token.
    """

    sub: str
    type: str
