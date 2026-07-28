import logging
from pathlib import Path

import pytest
from auth.deps import get_current_user
from auth.models import User
from database import get_session
from fastapi.testclient import TestClient
from main import create_app


@pytest.fixture(scope="session")
def session():
    yield from get_session()


def override_get_current_user():
    fake_user = User(
        username="johndoe", email="johndoe@example.fr", hashed_password="fake"
    )
    return fake_user


@pytest.fixture(scope="session")
def client():

    app = create_app(env_path=Path("tests/.env"))

    # Override authentication
    app.dependency_overrides[get_current_user] = override_get_current_user

    logger = logging.getLogger(__name__)
    logger.debug("Client is ready")

    return TestClient(app)
