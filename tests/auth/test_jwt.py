import logging
from datetime import timedelta

from auth.security import create_token, decode_token
from fastapi.testclient import TestClient
from sqlmodel import Session

from .factories import UserFactory


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


def register(client: TestClient, **overrides) -> dict:
    """
    Register a user with fake, unique credentials and return the request payload used.
    """

    data = build_register_payload(**overrides)

    response = client.post("/auth/register", data=data)
    assert response.status_code == 201

    return data


class TestJWT:

    def test_register(self, client: TestClient, session: Session):

        self.logger = logging.getLogger(__name__)

        data = build_register_payload()

        response = client.post("/auth/register", data=data)
        assert response.status_code == 201

        user = response.json()

        assert data["username"] == user["username"]

    def test_register_duplicate_username(self, auth_client: TestClient):

        data = register(auth_client)

        response = auth_client.post(
            "/auth/register",
            data={**data, "email": f"other_{data['email']}"},
        )
        assert response.status_code == 400

    def test_register_duplicate_email(self, auth_client: TestClient):

        data = register(auth_client)

        response = auth_client.post(
            "/auth/register",
            data={**data, "username": f"other_{data['username']}"},
        )
        assert response.status_code == 400

    def test_login_success(self, auth_client: TestClient):

        data = register(auth_client)

        response = auth_client.post(
            "/auth/login",
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

    def test_login_wrong_password(self, auth_client: TestClient):

        data = register(auth_client)

        response = auth_client.post(
            "/auth/login",
            data={"username": data["username"], "password": "WrongPassword_123!"},
        )
        assert response.status_code == 401

    def test_login_unknown_user(self, auth_client: TestClient):

        response = auth_client.post(
            "/auth/login",
            data={"username": "unknown_user", "password": "PassWord_123!"},
        )
        assert response.status_code == 401

    def test_refresh_token_success(self, auth_client: TestClient):

        data = register(auth_client)

        login_response = auth_client.post(
            "/auth/login",
            data={"username": data["username"], "password": data["password"]},
        )
        refresh_token = login_response.json()["refresh_token"]

        response = auth_client.post(
            "/auth/refresh", params={"refresh_token": refresh_token}
        )
        assert response.status_code == 200

        token = response.json()
        assert token["access_token"]
        assert token["refresh_token"]

        access_payload = decode_token(token["access_token"])
        assert access_payload is not None
        assert access_payload["type"] == "access"

    def test_refresh_token_rejects_access_token(self, auth_client: TestClient):

        data = register(auth_client)

        login_response = auth_client.post(
            "/auth/login",
            data={"username": data["username"], "password": data["password"]},
        )
        access_token = login_response.json()["access_token"]

        response = auth_client.post(
            "/auth/refresh", params={"refresh_token": access_token}
        )
        assert response.status_code == 401

    def test_refresh_token_invalid(self, auth_client: TestClient):

        response = auth_client.post(
            "/auth/refresh", params={"refresh_token": "not-a-valid-token"}
        )
        assert response.status_code == 401

    def test_read_current_user(self, auth_client: TestClient):

        data = register(auth_client)

        login_response = auth_client.post(
            "/auth/login",
            data={"username": data["username"], "password": data["password"]},
        )
        access_token = login_response.json()["access_token"]

        response = auth_client.get(
            "/users/me", headers={"Authorization": f"Bearer {access_token}"}
        )
        assert response.status_code == 200
        assert response.json()["username"] == data["username"]

    def test_read_current_user_without_token(self, auth_client: TestClient):

        response = auth_client.get("/users/me")
        assert response.status_code == 401

    def test_read_current_user_invalid_token(self, auth_client: TestClient):

        response = auth_client.get(
            "/users/me", headers={"Authorization": "Bearer not-a-valid-token"}
        )
        assert response.status_code == 401

    def test_read_current_user_rejects_refresh_token(self, auth_client: TestClient):

        data = register(auth_client)

        login_response = auth_client.post(
            "/auth/login",
            data={"username": data["username"], "password": data["password"]},
        )
        refresh_token = login_response.json()["refresh_token"]

        response = auth_client.get(
            "/users/me", headers={"Authorization": f"Bearer {refresh_token}"}
        )
        assert response.status_code == 401

    def test_create_and_decode_token_roundtrip(self):

        token = create_token(subject="test-subject", expires_delta=timedelta(minutes=5))
        payload = decode_token(token)

        assert payload is not None
        assert payload["sub"] == "test-subject"
        assert payload["type"] == "access"
