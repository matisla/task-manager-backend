from httpx2 import AsyncClient


class TestHealth:

    async def test_health_returns_ok_without_authentication(self, auth_client: AsyncClient):

        response = await auth_client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    async def test_api_health_returns_ok(self, auth_client: AsyncClient):

        response = await auth_client.get("/api/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
