import asyncio

from httpx import ASGITransport, AsyncClient, Response

from oceanscope_api.main import app


async def request(path: str) -> Response:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get(path)


def test_liveness_reports_process_status() -> None:
    response = asyncio.run(request("/health/live"))

    assert response.status_code == 200
    assert response.headers["x-correlation-id"]
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "oceanscope-api"


def test_readiness_reports_application_status() -> None:
    response = asyncio.run(request("/health/ready"))

    assert response.status_code == 200
    assert response.json()["status"] == "ready"
