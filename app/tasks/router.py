import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Form, Query, Response, status

from app.auth.deps import currentUserDep
from app.db.deps import SessionDep

from .filters import TaskFilter
from .models import Status
from .schemas import TaskCreate, TaskRead
from .services import TaskService

logger = structlog.get_logger(__name__)
tasks_router = APIRouter(prefix="/tasks", tags=["Tasks"])


@tasks_router.get("", response_model=list[TaskRead])
async def list_tasks(
    filters: Annotated[TaskFilter, Query()],
    user: currentUserDep,
    session: SessionDep,
):
    """
    List all tasks of the user, and filter them if based on given `filters`.

    Args:
        filters (TaskFilter): equality filters requested by the client.
        user (User): the authenticated user.
        session (Session): session used to access the database.

    Returns:
        list[TaskRead]: the tasks owned by the user.
    """

    return await TaskService.list(session, filters, user)


@tasks_router.post(
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
    Create a new task based on given `data`.

    Args:
        data (TaskCreate): data to use to create the task.
        user (User): the authenticated user, set as the task owner.
        session (Session): session used to access the database.

    Returns:
        TaskRead: the created task.
    """

    logger.debug("task_create", data=data)

    task = await TaskService.create(session, data, user)

    return task


@tasks_router.get(
    "/{task_id}",
    response_model=TaskRead,
)
async def detail_task(task_id: uuid.UUID, user: currentUserDep, session: SessionDep):
    """
    Get by id detail of a task.

    Args:
        task_id (uuid.UUID): id of the task to retrieve.
        user (User): the authenticated user.
        session (Session): session used to access the database.

    Returns:
        TaskRead: the requested task.
    """

    logger.debug("task_get", id=task_id)

    task = await TaskService.get_owned_or_404(session, task_id, user)

    return task


@tasks_router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_task(task_id: uuid.UUID, user: currentUserDep, session: SessionDep):
    """
    Delete a task by his id.

    Args:
        task_id (uuid.UUID): id of the task to delete.
        user (User): the authenticated user.
        session (Session): session used to access the database.

    Returns:
        Response: an empty 204 response.
    """

    logger.debug("task_delete", id=task_id)

    task = await TaskService.get_owned_or_404(session, task_id, user)
    await TaskService.delete(session, task)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@tasks_router.post(
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
    Move a task to a new status, validated against the allowed transitions graph.

    Args:
        task_id (uuid.UUID): id of the task to transition.
        target_status (Status): the requested target status.
        user (User): the authenticated user.
        session (Session): session used to access the database.

    Returns:
        TaskRead: the updated task.
    """

    logger.debug("task_change_status", id=task_id, target_status=target_status)

    task = await TaskService.get_owned_or_404(session, task_id, user)
    task = await TaskService.transition(session, task, target_status)

    return task
