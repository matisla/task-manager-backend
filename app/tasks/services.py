import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from auth.models import User
from core.exceptions import ConflictError, NotFoundError
from sqlmodel.ext.asyncio.session import AsyncSession

from .filters import TaskFilter
from .models import Status, Task
from .repository import TaskRepository
from .schemas import TaskCreate

ALLOWED_TRANSITIONS: dict[Status, frozenset[Status]] = {
    Status.BACKLOG: frozenset({Status.PLANNED, Status.CANCELLED}),
    Status.PLANNED: frozenset({Status.BACKLOG, Status.IN_PROGRESS, Status.CANCELLED}),
    Status.IN_PROGRESS: frozenset({Status.PAUSED, Status.WAITING, Status.DONE, Status.CANCELLED}),
    Status.PAUSED: frozenset({Status.IN_PROGRESS, Status.WAITING, Status.CANCELLED}),
    Status.WAITING: frozenset({Status.IN_PROGRESS, Status.PAUSED, Status.CANCELLED}),
    Status.DONE: frozenset({Status.ARCHIVED}),
    Status.CANCELLED: frozenset({Status.ARCHIVED}),
    Status.ARCHIVED: frozenset(),  # terminal, no outgoing transition
}


class TaskService:
    """
    Service handling task lifecycle: ownership resolution, status transitions and deletion.
    """

    @classmethod
    async def list(cls, session: AsyncSession, filters: TaskFilter, user: User) -> Sequence[Task]:
        """
        List tasks matching the given filters, scoped to the requesting user.

        Args:
            session (AsyncSession): session used to access the database.
            filters (TaskFilter): equality filters requested by the client.
            user (User): the requesting user; forced as the owner filter.

        Returns:
            Sequence[Task]: the matching tasks.
        """

        filters.user_id = user.id
        return await TaskRepository(session).list(filters)

    @classmethod
    async def create(cls, session: AsyncSession, data: TaskCreate, user: User) -> Task:
        """
        Create a new task owned by the given user.

        Args:
            session (AsyncSession): session used to access the database.
            data (TaskCreate): data to use to create the task.
            user (User): the requesting user, set as the task owner.

        Returns:
            Task: the created task.
        """

        return await TaskRepository(session).create(
            title=data.title,
            description=data.description or "",
            start_date=data.start_date,
            due_date=data.due_date,
            user_id=user.id,
            parent_id=data.parent_id,
        )

    @classmethod
    async def get_owned_or_404(cls, session: AsyncSession, task_id: uuid.UUID, user: User) -> Task:
        """
        Retrieve a task by id, scoped to its owner.

        Args:
            session (AsyncSession): session used to access the database.
            task_id (uuid.UUID): id of the task to retrieve.
            user (User): the requesting user, expected to own the task.

        Raises:
            NotFoundError: 404 if the task does not exist or is not owned by the user.

        Returns:
            Task: the retrieved task.
        """

        repository = TaskRepository(session)
        task = await repository.get(task_id)

        if task is None or task.user_id != user.id:
            raise NotFoundError("Task not found")

        return task

    @classmethod
    async def transition(cls, session: AsyncSession, task: Task, target: Status) -> Task:
        """
        Move a task to a new status, validated against ALLOWED_TRANSITIONS.

        Args:
            session (AsyncSession): session used to access the database.
            task (Task): task to transition.
            target (Status): the requested target status.

        Raises:
            ConflictError: 409 if the transition is not allowed from the current status.

        Returns:
            Task: the updated task.
        """

        if target not in ALLOWED_TRANSITIONS[task.status]:
            raise ConflictError(f"Cannot transition task from {task.status} to {target}")

        kwargs: dict = {"status": target}
        if target == Status.DONE:
            kwargs["completed_at"] = datetime.now(UTC)

        return await TaskRepository(session).update(task, **kwargs)

    @classmethod
    async def delete(cls, session: AsyncSession, task: Task) -> Task | None:
        """
        Apply the three-branch deletion rule.

        - BACKLOG: physical delete, returns None.
        - DONE / CANCELLED: implicit transition to ARCHIVED, returns the task.
        - ARCHIVED: idempotent no-op, returns the task unchanged (cf. Cas limites).
        - any other status: raises ConflictError 409.

        Args:
            session (AsyncSession): session used to access the database.
            task (Task): task to delete.

        Raises:
            ConflictError: 409 if the task is neither BACKLOG, DONE, CANCELLED nor ARCHIVED.

        Returns:
            Task | None: the archived task, or None if physically deleted.
        """

        match task.status:

            case Status.BACKLOG:
                await TaskRepository(session).delete(task)
                return None

            case Status.ARCHIVED:
                return task

            case Status.DONE | Status.CANCELLED:
                return await TaskRepository(session).update(task, status=Status.ARCHIVED)

            case _:
                raise ConflictError(f"Cannot delete task with status {task.status}")
