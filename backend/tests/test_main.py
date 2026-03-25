import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_kb_routes_registered():
    paths = {route.path for route in app.routes if hasattr(route, "path")}
    assert "/api/v1/kb/" in paths
