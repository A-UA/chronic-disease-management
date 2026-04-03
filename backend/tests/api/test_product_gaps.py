"""阶段2+3+4: 管理建议可见 + 密码重置 + 工作台补全 TDD 测试"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from app.api.deps import get_current_user, get_current_org, get_db, check_permission, get_current_org_user


def _dummy_user(uid=1001):
    u = MagicMock()
    u.id = uid
    u.email = "test@example.com"
    return u


def _mock_org_user():
    """模拟拥有全部权限的组织用户"""
    ou = MagicMock()
    ou.user_type = "staff"
    ou.org_id = 2001
    ou.user_id = 1001
    role = MagicMock()
    role.id = 1
    ou.rbac_roles = [role]
    return ou


def _async_override(app, db, uid=1001, org_id=2001):
    """统一设置异步依赖覆盖"""
    async def _user():
        return _dummy_user(uid)
    async def _org():
        return org_id
    async def _db():
        return db
    async def _org_user():
        return _mock_org_user()
    app.dependency_overrides[get_current_user] = _user
    app.dependency_overrides[get_current_org] = _org
    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_current_org_user] = _org_user


# ─── 阶段 2A：管理建议患者可见 ───

class TestPatientViewSuggestions:
    def _make_app(self):
        from app.api.endpoints.patients import router
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/patients")
        return app

    @pytest.mark.asyncio
    async def test_patient_sees_suggestions(self):
        """患者应能看到管理师给自己的建议"""
        app = self._make_app()
        patient = MagicMock()
        patient.id = 4001
        patient.user_id = 1001
        patient.org_id = 2001

        suggestion = MagicMock()
        suggestion.id = 8001
        suggestion.content = "建议每天监测血压"
        suggestion.suggestion_type = "clinical"
        suggestion.manager_id = 1002
        suggestion.patient_id = 4001
        suggestion.created_at = "2026-04-01T00:00:00"

        class DummyResult:
            def scalars(self):
                mock = MagicMock()
                mock.all.return_value = [suggestion]
                return mock

        db = AsyncMock()
        db.execute.side_effect = [
            type('R', (), {'scalar_one_or_none': lambda self: patient})(),
            DummyResult(),
        ]

        _async_override(app, db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/v1/patients/me/suggestions")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_no_suggestions_empty_list(self):
        """无建议时应返回空列表"""
        app = self._make_app()
        patient = MagicMock()
        patient.id = 4001
        patient.user_id = 1001
        patient.org_id = 2001

        class EmptyResult:
            def scalars(self):
                mock = MagicMock()
                mock.all.return_value = []
                return mock

        db = AsyncMock()
        db.execute.side_effect = [
            type('R', (), {'scalar_one_or_none': lambda self: patient})(),
            EmptyResult(),
        ]

        _async_override(app, db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/v1/patients/me/suggestions")

        assert resp.status_code == 200
        assert resp.json() == []


# ─── 阶段 3：密码重置 ───

class TestPasswordReset:
    def _make_app(self):
        from app.api.endpoints.auth import router
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/auth")
        return app

    @pytest.mark.asyncio
    async def test_forgot_password_always_200(self):
        """请求重置密码应始终返回 200（防止信息泄露）"""
        app = self._make_app()
        db = AsyncMock()
        db.execute.return_value = type('R', (), {
            'scalar_one_or_none': lambda self: None
        })()

        async def _db():
            return db
        app.dependency_overrides[get_db] = _db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post("/api/v1/auth/forgot-password",
                                 json={"email": "nonexistent@test.com"})

        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_reset_with_wrong_code(self):
        """错误验证码应返回 400"""
        app = self._make_app()
        db = AsyncMock()
        db.execute.return_value = type('R', (), {
            'scalar_one_or_none': lambda self: None
        })()

        async def _db():
            return db
        app.dependency_overrides[get_db] = _db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post("/api/v1/auth/reset-password", json={
                "email": "test@example.com",
                "code": "000000",
                "new_password": "NewPass123!",
            })

        assert resp.status_code == 400


# ─── 阶段 4A：管理师取消分配 ───

class TestManagerUnassign:
    def _make_app(self):
        from app.api.endpoints.managers import router
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/managers")
        return app

    @pytest.mark.asyncio
    @patch("app.api.deps.RBACService.get_effective_permissions", new_callable=AsyncMock, return_value={"org_member:manage"})
    async def test_unassign_success(self, mock_perms):
        """取消管理师分配应成功"""
        app = self._make_app()
        db = AsyncMock()
        db.execute.return_value = MagicMock(rowcount=1)

        _async_override(app, db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.delete("/api/v1/managers/assignments/4001")

        assert resp.status_code == 200

    @pytest.mark.asyncio
    @patch("app.api.deps.RBACService.get_effective_permissions", new_callable=AsyncMock, return_value={"org_member:manage"})
    async def test_unassign_not_found(self, mock_perms):
        """取消不存在的分配应返回 404"""
        app = self._make_app()
        db = AsyncMock()
        db.execute.return_value = MagicMock(rowcount=0)

        _async_override(app, db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.delete("/api/v1/managers/assignments/99999")

        assert resp.status_code == 404


# ─── 阶段 4B：家属解绑 ───

class TestFamilyUnlink:
    def _make_app(self):
        from app.api.endpoints.family import router
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/family")
        return app

    @pytest.mark.asyncio
    async def test_unlink_success(self):
        """家属解绑应成功"""
        app = self._make_app()
        link = MagicMock()
        link.patient_id = 4001
        link.family_user_id = 1001

        db = AsyncMock()
        db.execute.return_value = type('R', (), {
            'scalar_one_or_none': lambda self: link
        })()

        _async_override(app, db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.delete("/api/v1/family/links/4001")

        assert resp.status_code == 200
        db.delete.assert_called_once_with(link)


# ─── 阶段 4C：租户用量自查 ───

class TestTenantUsage:
    def _make_app(self):
        from app.api.endpoints.usage import router
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/usage")
        return app

    @pytest.mark.asyncio
    async def test_my_org_usage(self):
        """租户应能查看自己的用量"""
        app = self._make_app()
        org = MagicMock()
        org.quota_tokens_limit = 1000000
        org.quota_tokens_used = 12500

        db = AsyncMock()
        db.execute.return_value = MagicMock(
            scalar=MagicMock(return_value=12500)
        )
        db.get.return_value = org

        _async_override(app, db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/v1/usage/my-org")

        assert resp.status_code == 200
        data = resp.json()
        assert "total_tokens" in data


# ─── 阶段 4D：组织信息编辑 ───

class TestOrgUpdate:
    def _make_app(self):
        from app.api.endpoints.organizations import router
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/organizations")
        return app

    @pytest.mark.asyncio
    @patch("app.api.deps.RBACService.get_effective_permissions", new_callable=AsyncMock, return_value={"org:manage"})
    async def test_update_org_name(self, mock_perms):
        """编辑组织名称应成功"""
        app = self._make_app()
        org = MagicMock()
        org.id = 2001
        org.name = "旧名称"
        org.plan_type = "free"
        org.created_at = "2026-01-01T00:00:00"
        org.parent_id = None

        db = AsyncMock()
        db.get.return_value = org

        _async_override(app, db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.put("/api/v1/organizations/2001",
                                json={"name": "新名称"})

        assert resp.status_code == 200
        assert org.name == "新名称"
