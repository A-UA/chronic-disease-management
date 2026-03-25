import pytest
from httpx import AsyncClient, ASGITransport

from app.db.models import ManagerProfile, PatientProfile
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


def test_patient_profile_is_unique_per_org():
    unique_constraints = {
        tuple(column.name for column in constraint.columns)
        for constraint in PatientProfile.__table__.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }
    assert ("org_id", "user_id") in unique_constraints
    assert ("user_id",) not in unique_constraints


def test_manager_profile_is_unique_per_org():
    unique_constraints = {
        tuple(column.name for column in constraint.columns)
        for constraint in ManagerProfile.__table__.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }
    assert ("org_id", "user_id") in unique_constraints
    assert ("user_id",) not in unique_constraints
