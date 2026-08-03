import logging
import uuid

from httpx2 import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.models import User
from app.tasks.models import Task

from .factories import TaskFactory


class TestTask:
    async def test_create_task(self, client: AsyncClient, session: AsyncSession):
        """
        Test the basic creation of a task
        """

        self.logger = logging.getLogger(__name__)

        data = {
            "title": "first job",
            "description": "code the app",
        }
        response = await client.post("/api/tasks/", data=data)
        assert response.status_code == 201

        body = response.json()
        assert body["title"] == data["title"]
        assert body["description"] == data["description"]

        db_task = await session.get(Task, uuid.UUID(body["id"]))

        assert db_task is not None
        assert db_task.title == data["title"]

    async def test_list_tasks(self, client: AsyncClient):
        """
        Test the listing of tasks
        """

        self.logger = logging.getLogger(__name__)

        data = {
            "title": "task to list",
            "description": "should appear in the list",
        }
        created = await client.post("/api/tasks/", data=data)
        assert created.status_code == 201
        created_id = created.json()["id"]

        response = await client.get("/api/tasks/")
        assert response.status_code == 200

        tasks = response.json()
        assert any(task["id"] == created_id for task in tasks)

    async def test_list_tasks_with_factory(
        self, client: AsyncClient, session: AsyncSession, current_user: User
    ):
        """
        Test listing tasks generated with factory_boy
        """

        self.logger = logging.getLogger(__name__)

        tasks = TaskFactory.create_batch(3, user_id=current_user.id)
        session.add_all(tasks)
        await session.commit()

        response = await client.get("/api/tasks/")
        assert response.status_code == 200

        body = response.json()
        returned_ids = {task["id"] for task in body}

        assert {str(task.id) for task in tasks}.issubset(returned_ids)

    async def test_delete_task(self, client: AsyncClient, session: AsyncSession):

        self.logger = logging.getLogger(__name__)

        data = {
            "title": "task to delete",
            "description": "will be removed",
        }
        created = await client.post("/api/tasks/", data=data)
        assert created.status_code == 201
        task_id = created.json()["id"]

        response = await client.delete(f"/api/tasks/{task_id}")
        assert response.status_code == 204

        db_task = await session.get(Task, uuid.UUID(task_id))
        assert db_task is None
