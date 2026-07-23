from datetime import datetime

from pydantic import BaseModel, Field, EmailStr, ConfigDict


class UserCreate(BaseModel):
    """
    Schema for creating a new user
    """

    username: str = Field(min_length=3, max_length=63, example="johndoe")
    firstname: str = Field(min_length=1, max_length=64, example="John")
    lastname: str = Field(min_length=1, max_length=64, example="Doe")
    email: EmailStr = Field(example="johndoe@example.com")
    password: str = Field(min_length=8, example="SecuredPassword_123!")


class UserLogin(BaseModel):
    """
    Schema for login a user
    """

    username: str
    password: str


class UserResponse(BaseModel):
    id: int
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
