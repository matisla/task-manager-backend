import logging
import uuid

import pytest
from auth.models import User
from httpx2 import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession
from tasks.models import Status, Task
from tasks.services import ALLOWED_TRANSITIONS

from .factories import TaskFactory

VALID_TRANSITIONS = [
    (source, target) for source, targets in ALLOWED_TRANSITIONS.items() for target in targets
]

INVALID_TRANSITIONS = [
    *[(status, status) for status in Status],
    (Status.ARCHIVED, Status.DONE),
    (Status.ARCHIVED, Status.CANCELLED),
    (Status.ARCHIVED, Status.BACKLOG),
    (Status.DONE, Status.PLANNED),
    (Status.DONE, Status.BACKLOG),
    (Status.CANCELLED, Status.IN_PROGRESS),
]


class TestTaskLifecycle:
    async def _create_task(
        self, session: AsyncSession, user_id: uuid.UUID, status: Status = Status.BACKLOG
    ) -> Task:
        task = TaskFactory.create(user_id=user_id, status=status)
        session.add(task)
        await session.commit()
        await session.refresh(task)
        return task

    @pytest.mark.parametrize("source,target", VALID_TRANSITIONS)
    async def test_valid_transition(
        self,
        client: AsyncClient,
        session: AsyncSession,
        current_user: User,
        source: Status,
        target: Status,
    ):
        """
        Every edge declared in ALLOWED_TRANSITIONS should be accepted and return the new status.
        """

        self.logger = logging.getLogger(__name__)

        task = await self._create_task(session, current_user.id, status=source)

        response = await client.post(f"/api/tasks/{task.id}/{target.value}")
        assert response.status_code == 200
        assert response.json()["status"] == target.value

    @pytest.mark.parametrize("source,target", INVALID_TRANSITIONS)
    async def test_invalid_transition(
        self,
        client: AsyncClient,
        session: AsyncSession,
        current_user: User,
        source: Status,
        target: Status,
    ):
        """
        Transitions absent from ALLOWED_TRANSITIONS (including X -> X) should be rejected.
        """

        self.logger = logging.getLogger(__name__)

        task = await self._create_task(session, current_user.id, status=source)

        response = await client.post(f"/api/tasks/{task.id}/{target.value}")
        assert response.status_code == 409

    async def test_transition_to_done_sets_completed_at(
        self, client: AsyncClient, session: AsyncSession, current_user: User
    ):
        """
        IN_PROGRESS -> DONE should set completed_at.
        """

        self.logger = logging.getLogger(__name__)

        task = await self._create_task(session, current_user.id, status=Status.IN_PROGRESS)
        task_id = task.id
        assert task.completed_at is None

        response = await client.post(f"/api/tasks/{task_id}/{Status.DONE.value}")
        assert response.status_code == 200

        session.expire_all()
        db_task = await session.get(Task, task_id)
        assert db_task.completed_at is not None

    async def test_other_transitions_do_not_set_completed_at(
        self, client: AsyncClient, session: AsyncSession, current_user: User
    ):
        """
        Any transition other than X -> DONE should leave completed_at untouched (None).
        """

        self.logger = logging.getLogger(__name__)

        task = await self._create_task(session, current_user.id, status=Status.BACKLOG)
        task_id = task.id

        response = await client.post(f"/api/tasks/{task_id}/{Status.PLANNED.value}")
        assert response.status_code == 200

        session.expire_all()
        db_task = await session.get(Task, task_id)
        assert db_task.completed_at is None

    @pytest.mark.parametrize("source,target", VALID_TRANSITIONS)
    async def test_transition_does_not_set_updated_at(
        self,
        client: AsyncClient,
        session: AsyncSession,
        current_user: User,
        source: Status,
        target: Status,
    ):
        """
        No transition, explicit or implicit, should set updated_at (cf. Non-objectifs).
        """

        self.logger = logging.getLogger(__name__)

        task = await self._create_task(session, current_user.id, status=source)

        response = await client.post(f"/api/tasks/{task.id}/{target.value}")
        assert response.status_code == 200
        assert response.json()["updated_at"] is None

    async def test_delete_backlog_task_is_physical(
        self, client: AsyncClient, session: AsyncSession, current_user: User
    ):
        """
        DELETE on a BACKLOG task removes the row.
        """

        self.logger = logging.getLogger(__name__)

        task = await self._create_task(session, current_user.id, status=Status.BACKLOG)
        task_id = task.id

        response = await client.delete(f"/api/tasks/{task_id}")
        assert response.status_code == 204

        session.expire_all()
        assert await session.get(Task, task_id) is None

    @pytest.mark.parametrize("source", [Status.DONE, Status.CANCELLED])
    async def test_delete_done_or_cancelled_task_archives_it(
        self, client: AsyncClient, session: AsyncSession, current_user: User, source: Status
    ):
        """
        DELETE on a DONE/CANCELLED task is an implicit archiving, the row persists.
        """

        self.logger = logging.getLogger(__name__)

        task = await self._create_task(session, current_user.id, status=source)
        task_id = task.id

        response = await client.delete(f"/api/tasks/{task_id}")
        assert response.status_code == 204

        session.expire_all()
        db_task = await session.get(Task, task_id)
        assert db_task is not None
        assert db_task.status == Status.ARCHIVED

    async def test_delete_archived_task_is_idempotent(
        self, client: AsyncClient, session: AsyncSession, current_user: User
    ):
        """
        DELETE on an already ARCHIVED task is a no-op returning 204.
        """

        self.logger = logging.getLogger(__name__)

        task = await self._create_task(session, current_user.id, status=Status.ARCHIVED)
        task_id = task.id

        response = await client.delete(f"/api/tasks/{task_id}")
        assert response.status_code == 204

        session.expire_all()
        db_task = await session.get(Task, task_id)
        assert db_task is not None
        assert db_task.status == Status.ARCHIVED

    @pytest.mark.parametrize(
        "source",
        [Status.PLANNED, Status.IN_PROGRESS, Status.PAUSED, Status.WAITING],
    )
    async def test_delete_other_status_is_rejected(
        self, client: AsyncClient, session: AsyncSession, current_user: User, source: Status
    ):
        """
        DELETE on a task in any other status is rejected with 409, no change in database.
        """

        self.logger = logging.getLogger(__name__)

        task = await self._create_task(session, current_user.id, status=source)
        task_id = task.id

        response = await client.delete(f"/api/tasks/{task_id}")
        assert response.status_code == 409

        session.expire_all()
        db_task = await session.get(Task, task_id)
        assert db_task is not None
        assert db_task.status == source

    async def test_get_other_user_task_returns_404(
        self, client: AsyncClient, session: AsyncSession
    ):
        """
        GET on a task owned by another user returns 404.
        """

        self.logger = logging.getLogger(__name__)

        task = await self._create_task(session, uuid.uuid4(), status=Status.BACKLOG)

        response = await client.get(f"/api/tasks/{task.id}")
        assert response.status_code == 404

    async def test_delete_other_user_task_returns_404(
        self, client: AsyncClient, session: AsyncSession
    ):
        """
        DELETE on a task owned by another user returns 404.
        """

        self.logger = logging.getLogger(__name__)

        task = await self._create_task(session, uuid.uuid4(), status=Status.BACKLOG)

        response = await client.delete(f"/api/tasks/{task.id}")
        assert response.status_code == 404

    async def test_transition_other_user_task_returns_404(
        self, client: AsyncClient, session: AsyncSession
    ):
        """
        POST .../{status} on a task owned by another user returns 404.
        """

        self.logger = logging.getLogger(__name__)

        task = await self._create_task(session, uuid.uuid4(), status=Status.BACKLOG)

        response = await client.post(f"/api/tasks/{task.id}/{Status.PLANNED.value}")
        assert response.status_code == 404

    async def test_get_unknown_task_returns_404(self, client: AsyncClient):
        """
        GET on a non-existent task id returns 404.
        """

        self.logger = logging.getLogger(__name__)

        response = await client.get(f"/api/tasks/{uuid.uuid4()}")
        assert response.status_code == 404
