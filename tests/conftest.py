from functools import cache
from pathlib import Path

import pytest
import pytest_asyncio
from httpx2 import ASGITransport, AsyncClient
from sqlmodel import SQLModel

from app.auth.deps import get_current_user
from app.auth.models import User
from app.core.config import load_settings
from app.db.session import create_db_engine, create_session_factory
from app.main import create_app

from .auth.factories import UserFactory


@cache
def override_get_current_user() -> User:
    """Same fake user across requests, so ownership (eg. user_id) stays consistent."""

    return UserFactory.build()


@pytest.fixture(scope="session")
def current_user() -> User:
    return override_get_current_user()


@pytest_asyncio.fixture(scope="session")
async def engine():
    settings = load_settings(Path("tests/.env"))
    eng = create_db_engine(settings.db.connexion_url)

    async with eng.begin() as connection:
        await connection.run_sync(SQLModel.metadata.create_all)

    yield eng
    await eng.dispose()


@pytest_asyncio.fixture(scope="session")
async def session_factory(engine):
    return create_session_factory(engine)


@pytest_asyncio.fixture(scope="session")
async def session(session_factory):
    async with session_factory() as s:
        yield s


@pytest_asyncio.fixture(scope="session")
async def client(session_factory):
    """
    Client with authentication overridden to a fixed fake user (see `current_user`).
    """

    settings = load_settings(Path("tests/.env"))
    app = create_app(settings=settings)

    # Bypass the app's own lifespan (ASGITransport never triggers it); inject the
    # shared session_factory directly, matching what get_session() expects.
    app.state.session_factory = session_factory
    app.dependency_overrides[get_current_user] = override_get_current_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=True) as c:
        yield c


@pytest_asyncio.fixture(scope="session")
async def auth_client(session_factory):
    """
    Client without the authentication override, used to test the real JWT flow
    (login, refresh, and token verification on protected routes).
    """

    settings = load_settings(Path("tests/.env"))
    app = create_app(settings=settings)
    app.state.session_factory = session_factory

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=True) as c:
        yield c
