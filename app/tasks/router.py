import logging
import uuid
from datetime import UTC, datetime
from typing import Annotated

from auth.deps import currentUserDep
from database import SessionDep
from fastapi import APIRouter, Form, Response, status
from sqlmodel import select

from .models import Status, Task
from .schemas import TaskCreate, TaskRead
from .services import TaskService

router = APIRouter()


@router.get("", response_model=list[TaskRead])
async def list_tasks(user: currentUserDep, session: SessionDep):
    """
    Endpoint compatible OpenAPI / Swagger UI.
    List all tasks of the user.

    Args:
        user (User): the authenticated user.
        session (Session): session used to access the database.

    Returns:
        list[TaskRead]: the tasks owned by the user.
    """

    statement = select(Task).where(Task.user_id == user.id)
    tasks = session.exec(statement).all()

    return tasks


@router.post(
    "",
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
    Create a new task.

    Args:
        data (TaskCreate): data to use to create the task.
        user (User): the authenticated user, set as the task owner.
        session (Session): session used to access the database.

    Returns:
        TaskRead: the created task.
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


@router.get(
    "/{task_id}",
    response_model=TaskRead,
)
async def detail_task(task_id: uuid.UUID, user: currentUserDep, session: SessionDep):
    """
    Endpoint compatible OpenAPI / Swagger UI.
    Get detail of a task.

    Args:
        task_id (uuid.UUID): id of the task to retrieve.
        user (User): the authenticated user.
        session (Session): session used to access the database.

    Returns:
        TaskRead: the requested task.
    """

    logger = logging.getLogger(__name__)
    logger.debug(f"Try to get task: {task_id}")

    task = TaskService.get_owned_or_404(session, task_id, user)

    return task


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_task(task_id: uuid.UUID, user: currentUserDep, session: SessionDep):
    """
    Endpoint compatible OpenAPI / Swagger UI.
    Delete a task, following the three-branch deletion rule (see TaskService.delete):
    physical delete for BACKLOG, implicit archiving for DONE/CANCELLED, idempotent for
    ARCHIVED, 409 otherwise.

    Args:
        task_id (uuid.UUID): id of the task to delete.
        user (User): the authenticated user.
        session (Session): session used to access the database.

    Returns:
        Response: an empty 204 response.
    """

    logger = logging.getLogger(__name__)
    logger.debug(f"Try to delete a task: {task_id}")

    task = TaskService.get_owned_or_404(session, task_id, user)
    TaskService.delete(session, task)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{task_id}/{target_status}",
    response_model=TaskRead,
)
async def transition_task(
    task_id: uuid.UUID,
    target_status: Status,
    user: currentUserDep,
    session: SessionDep,
):
    """
    Endpoint compatible OpenAPI / Swagger UI.
    Move a task to a new status, validated against the allowed transitions graph.

    Args:
        task_id (uuid.UUID): id of the task to transition.
        target_status (Status): the requested target status.
        user (User): the authenticated user.
        session (Session): session used to access the database.

    Returns:
        TaskRead: the updated task.
    """

    logger = logging.getLogger(__name__)
    logger.debug(f"Try to transition task {task_id} to {target_status}")

    task = TaskService.get_owned_or_404(session, task_id, user)

    return TaskService.transition(session, task, target_status)
