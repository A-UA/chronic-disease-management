import pytest
from fastapi import FastAPI, Depends, Header
from httpx import AsyncClient, ASGITransport
from uuid import uuid4
import jwt
from datetime import datetime, timedelta, timezone

from app.api.deps import get_current_user, get_current_org
from app.core.config import settings
from app.core.security import ALGORITHM

app = FastAPI()

# Mock dependencies
async def mock_get_current_user(token: str = Header("Authorization")):
    return type("User", (), {"id": uuid4()})()

async def mock_get_current_org(x_organization_id: str = Header(...)):
    return x_organization_id

@app.get("/test-auth")
async def dummy_auth(user=Depends(mock_get_current_user)):
    return {"user_id": str(user.id)}

@app.get("/test-org")
async def dummy_org(org_id=Depends(mock_get_current_org)):
    return {"org_id": org_id}

@pytest.mark.asyncio
async def test_auth_dependency_mocked():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/test-auth", headers={"Authorization": "Bearer mocked_token"})
    assert response.status_code == 200
    assert "user_id" in response.json()

@pytest.mark.asyncio
async def test_org_dependency_mocked():
    org_id = str(uuid4())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/test-org", headers={"X-Organization-Id": org_id})
    assert response.status_code == 200
    assert response.json()["org_id"] == org_id
