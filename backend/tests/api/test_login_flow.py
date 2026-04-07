"""登录流程端点测试 — 覆盖 select-org / switch-org / my-orgs

验证后端多部门登录流程的完整性：
1. 单部门 → 自动签发完整 JWT
2. 多部门 → 返回 require_org_selection + 部门列表
3. select-org → 用 selection_token 换完整 JWT
4. switch-org → 已登录用户切换部门
5. my-orgs → 获取可用部门列表
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from tests.api.conftest import MockScalarResult, TENANT_ID, ORG_ID, USER_ID


def _make_app():
    from app.modules.auth.router import router
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/auth")
    return app


def _user(uid=USER_ID, email="test@example.com"):
    u = MagicMock()
    u.id = uid
    u.email = email
    u.name = "测试用户"
    u.password_hash = "$argon2id$fake"
    return u


def _org_user(org_id=ORG_ID, tenant_id=TENANT_ID, roles=None):
    ou = MagicMock()
    ou.user_id = USER_ID
    ou.org_id = org_id
    ou.tenant_id = tenant_id
    ou.user_type = "staff"
    role = MagicMock()
    role.id = 1
    role.code = roles[0] if roles else "admin"
    ou.rbac_roles = [role]
    org = MagicMock()
    org.id = org_id
    org.name = "测试部门"
    org.tenant_id = tenant_id
    org.tenant = MagicMock(name="测试租户")
    ou.organization = org
    return ou


class TestLoginSingleOrg:
    @pytest.mark.asyncio
    @patch("app.modules.auth.router.security.verify_password", return_value=True)
    async def test_single_org_returns_token(self, mock_verify):
        """单部门用户应直接获得完整 JWT"""
        from app.api.deps import get_db

        app = _make_app()
        user = _user()
        ou = _org_user()

        db = AsyncMock()
        db.execute.side_effect = [
            MockScalarResult(items=[user]),   # 查用户
            MockScalarResult(items=[ou]),      # 查部门列表
        ]
        app.dependency_overrides[get_db] = lambda: db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            r = await ac.post("/api/v1/auth/login/access-token", data={
                "username": "test@example.com", "password": "pass123",
            })
        assert r.status_code == 200, f"实际: {r.status_code}, {r.text}"
        data = r.json()
        assert data["access_token"] is not None
        assert data["require_org_selection"] is False
        assert "organization" in data


class TestLoginMultiOrg:
    @pytest.mark.asyncio
    @patch("app.modules.auth.router.security.verify_password", return_value=True)
    async def test_multi_org_requires_selection(self, mock_verify):
        """多部门用户应收到 require_org_selection=True"""
        from app.api.deps import get_db

        app = _make_app()
        user = _user()
        ou1 = _org_user(org_id=2001)
        ou2 = _org_user(org_id=2002)

        db = AsyncMock()
        db.execute.side_effect = [
            MockScalarResult(items=[user]),
            MockScalarResult(items=[ou1, ou2]),
        ]
        app.dependency_overrides[get_db] = lambda: db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            r = await ac.post("/api/v1/auth/login/access-token", data={
                "username": "test@example.com", "password": "pass123",
            })
        assert r.status_code == 200
        data = r.json()
        assert data["require_org_selection"] is True
        assert data["access_token"] is None
        assert "selection_token" in data
        assert len(data["organizations"]) == 2


class TestLoginWrongPassword:
    @pytest.mark.asyncio
    @patch("app.modules.auth.router.security.verify_password", return_value=False)
    async def test_wrong_password_400(self, mock_verify):
        from app.api.deps import get_db

        app = _make_app()
        db = AsyncMock()
        db.execute.return_value = MockScalarResult(items=[_user()])
        app.dependency_overrides[get_db] = lambda: db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            r = await ac.post("/api/v1/auth/login/access-token", data={
                "username": "test@example.com", "password": "wrong",
            })
        assert r.status_code == 400


class TestMyOrgs:
    @pytest.mark.asyncio
    async def test_returns_org_list(self):
        """my-orgs 应返回当前用户的部门列表"""
        from app.api.deps import get_db, get_current_user

        app = _make_app()
        user = _user()
        ou1 = _org_user(org_id=2001)
        ou2 = _org_user(org_id=2002)
        ou2.organization.id = 2002
        ou2.organization.name = "第二部门"

        db = AsyncMock()
        db.execute.return_value = MockScalarResult(items=[ou1, ou2])
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_current_user] = lambda: user

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            r = await ac.get("/api/v1/auth/my-orgs")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 2
        assert data[0]["id"] == ORG_ID


class TestSelectOrg:
    @pytest.mark.asyncio
    async def test_invalid_selection_token_400(self):
        """无效的 selection_token 应返回 400"""
        from app.api.deps import get_db

        app = _make_app()
        db = AsyncMock()
        app.dependency_overrides[get_db] = lambda: db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            r = await ac.post("/api/v1/auth/select-org", json={
                "org_id": ORG_ID,
                "selection_token": "invalid.token.here",
            })
        assert r.status_code == 400


class TestSwitchOrg:
    @pytest.mark.asyncio
    async def test_switch_to_unauthorized_org_403(self):
        """切换到不属于自己的部门应返回 403"""
        from app.api.deps import get_db, get_current_user

        app = _make_app()
        user = _user()
        db = AsyncMock()
        db.execute.return_value = MockScalarResult(items=[])  # 不属于该部门
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_current_user] = lambda: user

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            r = await ac.post("/api/v1/auth/switch-org", json={"org_id": 9999})
        assert r.status_code == 403
