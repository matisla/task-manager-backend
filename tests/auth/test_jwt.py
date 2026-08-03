import logging
import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from httpx2 import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.repository import UserRepository
from app.auth.security import create_token, decode_token
from app.core.config import get_settings

from .factories import UserFactory


def make_token(**payload) -> str:
    """
    Build a raw JWT from an arbitrary payload, bypassing `create_token`'s defaults.
    """

    settings = get_settings()
    return jwt.encode(payload, settings.auth.SECRET_KEY, algorithm=settings.auth.ALGORITHM)


def build_register_payload(**overrides) -> dict:
    """
    Build a registration payload with fake, unique credentials.
    """

    fake_user = UserFactory.build()
    data = {
        "username": fake_user.username,
        "password": "PassWord_123!",
        "email": fake_user.email,
        "firstname": fake_user.firstname,
        "lastname": fake_user.lastname,
        **overrides,
    }

    return data


async def register(client: AsyncClient, **overrides) -> dict:
    """
    Register a user with fake, unique credentials and return the request payload used.
    """

    data = build_register_payload(**overrides)

    response = await client.post("/api/auth/register", data=data)
    assert response.status_code == 201

    return data


class TestJWT:
    async def test_register(self, client: AsyncClient, session: AsyncSession):

        self.logger = logging.getLogger(__name__)

        data = build_register_payload()

        response = await client.post("/api/auth/register", data=data)
        assert response.status_code == 201

        user = response.json()

        assert data["username"] == user["username"]

    async def test_register_without_firstname_and_lastname(self, auth_client: AsyncClient):
        """
        UserResponse must serialize a user with no firstname/lastname (both nullable on
        the User model), regression test for the firstname/lastname nullability mismatch.
        """

        fake_user = UserFactory.build()
        data = {
            "username": fake_user.username,
            "password": "PassWord_123!",
            "email": fake_user.email,
        }

        response = await auth_client.post("/api/auth/register", data=data)
        assert response.status_code == 201

        user = response.json()
        assert user["firstname"] is None
        assert user["lastname"] is None

    async def test_register_duplicate_username(self, auth_client: AsyncClient):

        data = await register(auth_client)

        response = await auth_client.post(
            "/api/auth/register",
            data={**data, "email": f"other_{data['email']}"},
        )
        assert response.status_code == 400

    async def test_register_duplicate_email(self, auth_client: AsyncClient):

        data = await register(auth_client)

        response = await auth_client.post(
            "/api/auth/register",
            data={**data, "username": f"other_{data['username']}"},
        )
        assert response.status_code == 400

    async def test_login_success(self, auth_client: AsyncClient):

        data = await register(auth_client)

        response = await auth_client.post(
            "/api/auth/login",
            data={"username": data["username"], "password": data["password"]},
        )
        assert response.status_code == 200

        token = response.json()
        assert token["token_type"] == "bearer"
        assert token["access_token"]
        assert token["refresh_token"]

        access_payload = decode_token(token["access_token"])
        assert access_payload is not None
        assert access_payload["type"] == "access"

        refresh_payload = decode_token(token["refresh_token"])
        assert refresh_payload is not None
        assert refresh_payload["type"] == "refresh"

    async def test_login_wrong_password(self, auth_client: AsyncClient):

        data = await register(auth_client)

        response = await auth_client.post(
            "/api/auth/login",
            data={"username": data["username"], "password": "WrongPassword_123!"},
        )
        assert response.status_code == 401

    async def test_login_unknown_user(self, auth_client: AsyncClient):

        response = await auth_client.post(
            "/api/auth/login",
            data={"username": "unknown_user", "password": "PassWord_123!"},
        )
        assert response.status_code == 401

    async def test_refresh_token_success(self, auth_client: AsyncClient):

        data = await register(auth_client)

        login_response = await auth_client.post(
            "/api/auth/login",
            data={"username": data["username"], "password": data["password"]},
        )
        refresh_token = login_response.json()["refresh_token"]

        response = await auth_client.post(
            "/api/auth/refresh", params={"refresh_token": refresh_token}
        )
        assert response.status_code == 200

        token = response.json()
        assert token["access_token"]
        assert token["refresh_token"]

        access_payload = decode_token(token["access_token"])
        assert access_payload is not None
        assert access_payload["type"] == "access"

    async def test_refresh_token_rejects_access_token(self, auth_client: AsyncClient):

        data = await register(auth_client)

        login_response = await auth_client.post(
            "/api/auth/login",
            data={"username": data["username"], "password": data["password"]},
        )
        access_token = login_response.json()["access_token"]

        response = await auth_client.post(
            "/api/auth/refresh", params={"refresh_token": access_token}
        )
        assert response.status_code == 401

    async def test_refresh_token_invalid(self, auth_client: AsyncClient):

        response = await auth_client.post(
            "/api/auth/refresh", params={"refresh_token": "not-a-valid-token"}
        )
        assert response.status_code == 401

    async def test_read_current_user(self, auth_client: AsyncClient):

        data = await register(auth_client)

        login_response = await auth_client.post(
            "/api/auth/login",
            data={"username": data["username"], "password": data["password"]},
        )
        access_token = login_response.json()["access_token"]

        response = await auth_client.get(
            "/api/users/me", headers={"Authorization": f"Bearer {access_token}"}
        )
        assert response.status_code == 200
        assert response.json()["username"] == data["username"]

    async def test_read_current_user_without_token(self, auth_client: AsyncClient):

        response = await auth_client.get("/api/users/me")
        assert response.status_code == 401

    async def test_read_current_user_invalid_token(self, auth_client: AsyncClient):

        response = await auth_client.get(
            "/api/users/me", headers={"Authorization": "Bearer not-a-valid-token"}
        )
        assert response.status_code == 401

    async def test_read_current_user_rejects_refresh_token(self, auth_client: AsyncClient):

        data = await register(auth_client)

        login_response = await auth_client.post(
            "/api/auth/login",
            data={"username": data["username"], "password": data["password"]},
        )
        refresh_token = login_response.json()["refresh_token"]

        response = await auth_client.get(
            "/api/users/me", headers={"Authorization": f"Bearer {refresh_token}"}
        )
        assert response.status_code == 401

    def test_create_and_decode_token_roundtrip(self):

        token = create_token(subject="test-subject", expires_delta=timedelta(minutes=5))
        payload = decode_token(token)

        assert payload is not None
        assert payload["sub"] == "test-subject"
        assert payload["type"] == "access"

    async def test_read_current_user_token_without_subject(self, auth_client: AsyncClient):

        token = make_token(type="access", exp=datetime.now(UTC) + timedelta(minutes=5))

        response = await auth_client.get(
            "/api/users/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 401

    async def test_read_current_user_token_with_malformed_subject(self, auth_client: AsyncClient):

        token = create_token(subject="not-a-uuid", expires_delta=timedelta(minutes=5))

        response = await auth_client.get(
            "/api/users/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 401

    async def test_read_current_user_unknown_subject(self, auth_client: AsyncClient):

        token = create_token(subject=str(uuid.uuid4()), expires_delta=timedelta(minutes=5))

        response = await auth_client.get(
            "/api/users/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 401

    async def test_read_current_user_deactivated(
        self, auth_client: AsyncClient, session: AsyncSession
    ):

        data = await register(auth_client)

        login_response = await auth_client.post(
            "/api/auth/login",
            data={"username": data["username"], "password": data["password"]},
        )
        access_token = login_response.json()["access_token"]

        db_user = await UserRepository(session).get_by("username", data["username"])
        assert db_user is not None
        db_user.is_active = False
        session.add(db_user)
        await session.commit()

        response = await auth_client.get(
            "/api/users/me", headers={"Authorization": f"Bearer {access_token}"}
        )
        assert response.status_code == 400

    async def test_get_by_invalid_attribute(self, session: AsyncSession):

        with pytest.raises(AttributeError):
            await UserRepository(session).get_by("bogus_attribute", "value")
