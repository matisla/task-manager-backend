import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """
    Schema for creating a new user
    """

    username: str = Field(min_length=3, max_length=63, examples=["johndoe"])
    firstname: str | None = Field(
        min_length=1, max_length=64, default=None, examples=["John"]
    )
    lastname: str | None = Field(
        min_length=1, max_length=64, default=None, examples=["Doe"]
    )
    email: EmailStr = Field(examples=["johndoe@example.com"])
    password: str = Field(min_length=8, examples=["SecuredPassword_123!"])


class UserLogin(BaseModel):
    """
    Schema for login a user
    """

    username: str
    password: str


class UserResponse(BaseModel):
    id: uuid.UUID
    username: str
    firstname: str
    lastname: str
    email: EmailStr
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str
    type: str
