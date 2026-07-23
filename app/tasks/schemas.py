from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, validator


class Tag(BaseModel):
    name: str = Field(, max_length=64)


class TaskBase(BaseModel):
    pass
    


class Task(BaseModel):
    id: int
    title: str = Field(max_length=256)
    description: Optional[str] = None
    created_at = Field()
    due_date: Optional[datetime] = Field()
    start_date: Optional[datetime] = Field()

    @validator("created_at", pre=True, always=True)
    def default_datetime(cls, value: datetime) -> datetime:
        return value or datetime.now()
