import logging
from datetime import UTC, datetime
from typing import Annotated

from auth.deps import currentUserDep
from database import SessionDep
from fastapi import APIRouter, Form, Response, status
from sqlmodel import select

from .models import Task
from .schemas import TaskCreate, TaskRead

router = APIRouter()


@router.get("/tasks", response_model=TaskRead)
async def list_tasks(user: currentUserDep, session: SessionDep):
    """
    Endpoint compatible OpenAPI / Swagger UI.
    List all tasks of the user
    """

    statement = select(Task).where(Task.user_id == user.id)
    tasks = session.exec(statement)

    return tasks


@router.post(
    "/tasks",
    status_code=status.HTTP_201_CREATED,
    response_model=TaskRead,
)
async def create_task(
    data: Annotated[TaskCreate, Form()],
    user: currentUserDep,
    session: SessionDep,
):
    """
    Endpoint compatible OpenAPI / Swagger UI.
    Create a new task
    """

    logger = logging.getLogger(__name__)
    logger.debug(f"Try to create a new task: {data}")

    db_task = Task(
        title=data.title,
        description=data.description or "",
        created_at=datetime.now(UTC),
        start_date=data.start_date,
        due_date=data.due_date,
        user_id=user.id,
        parent_id=data.parent_id,
    )

    session.add(db_task)
    session.commit()
    session.refresh(db_task)

    return db_task


@router.delete(
    "/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_task(task_id, user: currentUserDep, session: SessionDep):
    """
    Endpoint compatible OpenAPI / Swagger UI.
    Create a new task
    """

    logger = logging.getLogger(__name__)
    logger.debug(f"Try to delete a task: {task_id}")

    task = session.get(Task, task_id)

    session.delete(task)
    session.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
