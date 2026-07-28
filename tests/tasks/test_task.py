import logging
import uuid

from auth.models import User
from fastapi.testclient import TestClient
from sqlmodel import Session
from factories import TaskFactory
from tasks.models import Task


class TestTask:

    def test_create_task(self, client: TestClient, session: Session):
        """
        Test the basic creation of a task
        """

        self.logger = logging.getLogger(__name__)

        data = {
            "title": "first job",
            "description": "code the app",
        }
        response = client.post("/tasks/", data=data)
        assert response.status_code == 201

        body = response.json()
        assert body["title"] == data["title"]
        assert body["description"] == data["description"]

        db_task = session.get(Task, uuid.UUID(body["id"]))

        assert db_task is not None
        assert db_task.title == data["title"]

    def test_list_tasks(self, client: TestClient):
        """
        Test the listing of tasks
        """

        self.logger = logging.getLogger(__name__)

        data = {
            "title": "task to list",
            "description": "should appear in the list",
        }
        created = client.post("/tasks/", data=data)
        assert created.status_code == 201
        created_id = created.json()["id"]

        response = client.get("/tasks/")
        assert response.status_code == 200

        tasks = response.json()
        assert any(task["id"] == created_id for task in tasks)

    def test_list_tasks_with_factory(
        self, client: TestClient, session: Session, current_user: User
    ):
        """
        Test listing tasks generated with factory_boy
        """

        self.logger = logging.getLogger(__name__)

        tasks = TaskFactory.create_batch(3, user_id=current_user.id)
        session.add_all(tasks)
        session.commit()

        response = client.get("/tasks/")
        assert response.status_code == 200

        body = response.json()
        returned_ids = {task["id"] for task in body}

        assert {str(task.id) for task in tasks}.issubset(returned_ids)

    def test_delete_task(self, client: TestClient, session: Session):

        self.logger = logging.getLogger(__name__)

        data = {
            "title": "task to delete",
            "description": "will be removed",
        }
        created = client.post("/tasks/", data=data)
        assert created.status_code == 201
        task_id = created.json()["id"]

        response = client.delete(f"/tasks/{task_id}")
        assert response.status_code == 204

        db_task = session.get(Task, uuid.UUID(task_id))
        assert db_task is None
