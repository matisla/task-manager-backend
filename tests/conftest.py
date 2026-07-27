import logging
from pathlib import Path

import pytest
from database import get_session
from fastapi.testclient import TestClient
from main import create_app


@pytest.fixture(scope="session")
def session():
    return get_session()


@pytest.fixture(scope="session")
def client():

    app = create_app(env_path=Path("tests/.env"))

    logger = logging.getLogger(__name__)
    logger.debug("Client is ready")

    return TestClient(app)
