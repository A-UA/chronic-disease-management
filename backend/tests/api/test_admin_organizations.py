from uuid import uuid4
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_user, get_db
from app.api.endpoints.admin.organizations import router


app = FastAPI()
app.include_router(router, prefix="/api/v1")


class DummyUser:
    def __init__(self):
        self.id = uuid4()


class DummyMemberUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "member@example.com"
        self.name = "Member"


class DummyScalarResult:
    def __init__(self, one=None, many=None):
        self._one = one
        self._many = many or []

    def scalar_one_or_none(self):
        return self._one

    def scalars(self):
        result = MagicMock()
        result.all.return_value = self._many
        return result


class DummyDB:
    def __init__(self, results):
        self._results = list(results)

    async def execute(self, stmt):
        return self._results.pop(0)


current_user = DummyUser()


def _member(role_codes, user_type="staff"):
    role_objects = []
    for code in role_codes:
        role = MagicMock()
        role.code = code
        role_objects.append(role)

    org_user = MagicMock()
    org_user.user = DummyMemberUser()
    org_user.rbac_roles = role_objects
    org_user.user_type = user_type
    return org_user


@pytest.mark.asyncio
async def test_get_organization_members_returns_structured_roles():
    org_id = uuid4()
    member = _member(["admin", "manager"])
    db = DummyDB([
        DummyScalarResult(one=MagicMock()),
        DummyScalarResult(many=[member]),
    ])

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: current_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get(f"/api/v1/{org_id}/members")

    assert resp.status_code == 200
    payload = resp.json()
    assert payload[0]["roles"] == ["admin", "manager"]
    assert payload[0]["user_type"] == "staff"
    assert "role" not in payload[0]
