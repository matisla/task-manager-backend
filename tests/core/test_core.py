from fastapi.testclient import TestClient


class TestHealth:

    def test_health_returns_ok_without_authentication(self, auth_client: TestClient):

        response = auth_client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
