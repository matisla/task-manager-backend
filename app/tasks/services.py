import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from auth.models import User
from core.exceptions import ConflictError, NotFoundError
from sqlmodel import Session

from .filters import TaskFilter
from .models import Status, Task
from .repositories import TaskRepository
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
    def list(cls, session: Session, filters: TaskFilter, user: User) -> Sequence[Task]:
        """
        List tasks matching the given filters, scoped to the requesting user.

        Args:
            session (Session): session used to access the database.
            filters (TaskFilter): equality filters requested by the client.
            user (User): the requesting user; forced as the owner filter.

        Returns:
            Sequence[Task]: the matching tasks.
        """

        filters.user_id = user.id
        return TaskRepository(session).list(filters)

    @classmethod
    def create(cls, session: Session, data: TaskCreate, user: User) -> Task:
        """
        Create a new task owned by the given user.

        Args:
            session (Session): session used to access the database.
            data (TaskCreate): data to use to create the task.
            user (User): the requesting user, set as the task owner.

        Returns:
            Task: the created task.
        """

        return TaskRepository(session).create(
            title=data.title,
            description=data.description or "",
            start_date=data.start_date,
            due_date=data.due_date,
            user_id=user.id,
            parent_id=data.parent_id,
        )

    @classmethod
    def get_owned_or_404(cls, session: Session, task_id: uuid.UUID, user: User) -> Task:
        """
        Retrieve a task by id, scoped to its owner.

        Args:
            session (Session): session used to access the database.
            task_id (uuid.UUID): id of the task to retrieve.
            user (User): the requesting user, expected to own the task.

        Raises:
            NotFoundError: 404 if the task does not exist or is not owned by the user.

        Returns:
            Task: the retrieved task.
        """

        repository = TaskRepository(session)
        task = repository.get(task_id)

        if task is None or task.user_id != user.id:
            raise NotFoundError("Task not found")

        return task

    @classmethod
    def transition(cls, session: Session, task: Task, target: Status) -> Task:
        """
        Move a task to a new status, validated against ALLOWED_TRANSITIONS.

        Args:
            session (Session): session used to access the database.
            task (Task): task to transition.
            target (Status): the requested target status.

        Raises:
            ConflictError: 409 if the transition is not allowed from the current status.

        Returns:
            Task: the updated task.
        """

        if target not in ALLOWED_TRANSITIONS[task.status]:
            raise ConflictError(f"Cannot transition task from {task.status} to {target}")

        task.status = target

        if target == Status.DONE:
            task.completed_at = datetime.now(UTC)

        session.add(task)
        session.commit()
        session.refresh(task)

        return task

    @classmethod
    def delete(cls, session: Session, task: Task) -> Task | None:
        """
        Apply the three-branch deletion rule.

        - BACKLOG: physical delete, returns None.
        - DONE / CANCELLED: implicit transition to ARCHIVED, returns the task.
        - ARCHIVED: idempotent no-op, returns the task unchanged (cf. Cas limites).
        - any other status: raises ConflictError 409.

        Args:
            session (Session): session used to access the database.
            task (Task): task to delete.

        Raises:
            ConflictError: 409 if the task is neither BACKLOG, DONE, CANCELLED nor ARCHIVED.

        Returns:
            Task | None: the archived task, or None if physically deleted.
        """

        match task.status:

            case Status.BACKLOG:
                session.delete(task)
                session.commit()
                return None

            case Status.ARCHIVED:
                return task

            case Status.DONE | Status.CANCELLED:
                task.status = Status.ARCHIVED
                session.add(task)
                session.commit()
                session.refresh(task)
                return task

            case _:
                raise ConflictError(f"Cannot delete task with status {task.status}")
