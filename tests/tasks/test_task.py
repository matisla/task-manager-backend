import logging

from fastapi.testclient import TestClient
from sqlmodel import Session

from tasks.models import Task


class TestTask:

    def test_register(self, client: TestClient, session: Session):

        self.logger = logging.getLogger(__name__)

        data = {
            "title": "first job",
            "description": "code the app",
        }
        response = client.post("/tasks/", data=data)
        assert response.status_code == 201
