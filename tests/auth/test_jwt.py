import logging
import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session

from auth.models import User


class TestJWT:

    def test_register(self, client: TestClient, session: Session):

        self.logger = logging.getLogger(__name__)

        data = {
            "username": "johndoe",
            "password": "PassWord_123!",
            "email": "johndoe@example.com",
            "firstname": "John",
            "lastname": "Doe",
        }

        response = client.post("/auth/register", data=data)
        assert response.status_code == 201

        user = response.json()

        db_user = session.get(User, uuid.UUID(user["id"]))

        assert db_user.username == user["username"]
