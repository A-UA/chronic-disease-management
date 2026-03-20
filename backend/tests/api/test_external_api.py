import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock
from app.api.endpoints.external_api import router
from app.api.deps import get_db

app = FastAPI()
app.include_router(router, prefix="/v1")

async def mock_get_db():
    class MockResult:
        def scalar_one_or_none(self):
            return None
    class MockDB:
        async def execute(self, *args, **kwargs):
            return MockResult()
    yield MockDB()

app.dependency_overrides[get_db] = mock_get_db

@pytest.mark.asyncio
async def test_external_api_auth_failure():
    # Calling without mock, should hit the dependency and fail auth at DB level or header
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/v1/chat/completions", json={"kb_id": "00000000-0000-0000-0000-000000000000", "query": "test"}, headers={"Authorization": "Bearer fake_key"})
    assert response.status_code == 401 
