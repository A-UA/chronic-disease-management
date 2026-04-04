"""CRUD 补全测试

覆盖：
- ManagerProfile CRUD
- PatientProfile 创建/删除
- ManagementSuggestion 更新/删除
- Role 更新/删除
"""
import pytest
from unittest.mock import MagicMock, AsyncMock
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from tests.api.conftest import (
    override_deps, MockScalarResult, PatchRBAC,
    TENANT_ID, ORG_ID, USER_ID,
)


# ═══════════════════════════════════════════
# Task 1: ManagerProfile CRUD
# ═══════════════════════════════════════════

class TestManagerProfileCreate:
    def _make_app(self):
        from app.api.endpoints.managers import router
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/managers")
        return app

    @pytest.mark.asyncio
    async def test_create_ok(self):
        app = self._make_app()
        target_user = MagicMock()
        target_user.id = 1002

        db = AsyncMock()
        db.execute.side_effect = [
            MockScalarResult(items=[target_user]),  # 用户存在
            MockScalarResult(items=[]),              # 无重复
        ]
        db.refresh = AsyncMock()
        db.add = MagicMock()
        override_deps(app, db=db)

        with PatchRBAC():
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
                r = await ac.post("/api/v1/managers/profiles", json={
                    "user_id": 1002, "title": "主任管理师", "bio": "10年经验",
                })
        assert r.status_code == 200, f"实际: {r.status_code}, {r.text}"
        db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_duplicate_409(self):
        app = self._make_app()
        target_user = MagicMock()
        target_user.id = 1002

        db = AsyncMock()
        db.execute.side_effect = [
            MockScalarResult(items=[target_user]),
            MockScalarResult(items=[MagicMock()]),
        ]
        override_deps(app, db=db)

        with PatchRBAC():
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
                r = await ac.post("/api/v1/managers/profiles", json={
                    "user_id": 1002, "title": "管理师",
                })
        assert r.status_code == 409


class TestManagerProfileUpdate:
    def _make_app(self):
        from app.api.endpoints.managers import router
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/managers")
        return app

    @pytest.mark.asyncio
    async def test_update_title(self):
        app = self._make_app()
        profile = MagicMock()
        profile.id = 3001
        profile.user_id = 1002
        profile.tenant_id = TENANT_ID
        profile.org_id = ORG_ID
        profile.title = "旧职称"
        profile.bio = "旧简介"
        profile.is_active = True

        db = AsyncMock()
        db.get.return_value = profile
        override_deps(app, db=db)

        with PatchRBAC():
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
                r = await ac.put("/api/v1/managers/profiles/3001", json={"title": "高级管理师"})
        assert r.status_code == 200, f"实际: {r.status_code}, {r.text}"
        assert profile.title == "高级管理师"

    @pytest.mark.asyncio
    async def test_update_not_found_404(self):
        app = self._make_app()
        db = AsyncMock()
        db.get.return_value = None
        override_deps(app, db=db)

        with PatchRBAC():
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
                r = await ac.put("/api/v1/managers/profiles/99999", json={"title": "不存在"})
        assert r.status_code == 404


class TestManagerProfileDelete:
    def _make_app(self):
        from app.api.endpoints.managers import router
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/managers")
        return app

    @pytest.mark.asyncio
    async def test_deactivate(self):
        app = self._make_app()
        profile = MagicMock()
        profile.id = 3001
        profile.tenant_id = TENANT_ID
        profile.org_id = ORG_ID
        profile.is_active = True

        db = AsyncMock()
        db.get.return_value = profile
        override_deps(app, db=db)

        with PatchRBAC():
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
                r = await ac.delete("/api/v1/managers/profiles/3001")
        assert r.status_code == 200
        assert profile.is_active is False


# ═══════════════════════════════════════════
# Task 2: PatientProfile 创建+删除
# ═══════════════════════════════════════════

class TestPatientProfileCreate:
    def _make_app(self):
        from app.api.endpoints.patients import router
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/patients")
        return app

    @pytest.mark.asyncio
    async def test_admin_create(self):
        app = self._make_app()
        target_user = MagicMock()
        target_user.id = 1003

        db = AsyncMock()
        db.execute.side_effect = [
            MockScalarResult(items=[target_user]),
            MockScalarResult(items=[]),
        ]
        db.refresh = AsyncMock()
        db.add = MagicMock()
        override_deps(app, db=db)

        with PatchRBAC():
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
                r = await ac.post("/api/v1/patients/create", json={
                    "user_id": 1003, "real_name": "张三", "gender": "male",
                })
        assert r.status_code == 200, f"实际: {r.status_code}, {r.text}"
        db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_duplicate_409(self):
        app = self._make_app()
        target_user = MagicMock()
        target_user.id = 1003

        db = AsyncMock()
        db.execute.side_effect = [
            MockScalarResult(items=[target_user]),
            MockScalarResult(items=[MagicMock()]),
        ]
        override_deps(app, db=db)

        with PatchRBAC():
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
                r = await ac.post("/api/v1/patients/create", json={
                    "user_id": 1003, "real_name": "张三",
                })
        assert r.status_code == 409


class TestPatientProfileDelete:
    def _make_app(self):
        from app.api.endpoints.patients import router
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/patients")
        return app

    @pytest.mark.asyncio
    async def test_delete_ok(self):
        app = self._make_app()
        profile = MagicMock()
        profile.id = 4001
        profile.tenant_id = TENANT_ID
        profile.org_id = ORG_ID

        db = AsyncMock()
        db.get.return_value = profile
        override_deps(app, db=db)

        with PatchRBAC():
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
                r = await ac.delete("/api/v1/patients/4001")
        assert r.status_code == 200
        db.delete.assert_called_once_with(profile)

    @pytest.mark.asyncio
    async def test_delete_not_found_404(self):
        app = self._make_app()
        db = AsyncMock()
        db.get.return_value = None
        override_deps(app, db=db)

        with PatchRBAC():
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
                r = await ac.delete("/api/v1/patients/99999")
        assert r.status_code == 404


# ═══════════════════════════════════════════
# Task 3: ManagementSuggestion 更新+删除
# ═══════════════════════════════════════════

def _suggestion(sid=8001, manager_id=USER_ID, tenant_id=TENANT_ID):
    s = MagicMock()
    s.id = sid
    s.manager_id = manager_id
    s.content = "旧建议"
    s.suggestion_type = "general"
    s.patient_id = 4001
    s.tenant_id = tenant_id
    s.org_id = ORG_ID
    s.created_at = "2026-04-01T00:00:00"
    return s


class TestSuggestionUpdate:
    def _make_app(self):
        from app.api.endpoints.managers import router
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/managers")
        return app

    @pytest.mark.asyncio
    async def test_update_own(self):
        app = self._make_app()
        suggestion = _suggestion()
        db = AsyncMock()
        db.get.return_value = suggestion
        override_deps(app, db=db)

        with PatchRBAC():
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
                r = await ac.put("/api/v1/managers/suggestions/8001",
                                 json={"content": "更新后的建议"})
        assert r.status_code == 200, f"实际: {r.status_code}, {r.text}"
        assert suggestion.content == "更新后的建议"

    @pytest.mark.asyncio
    async def test_update_others_403(self):
        app = self._make_app()
        suggestion = _suggestion(manager_id=9999)
        db = AsyncMock()
        db.get.return_value = suggestion
        override_deps(app, db=db)

        with PatchRBAC():
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
                r = await ac.put("/api/v1/managers/suggestions/8001",
                                 json={"content": "恶意修改"})
        assert r.status_code == 403


class TestSuggestionDelete:
    def _make_app(self):
        from app.api.endpoints.managers import router
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/managers")
        return app

    @pytest.mark.asyncio
    async def test_delete_own(self):
        app = self._make_app()
        suggestion = _suggestion()
        db = AsyncMock()
        db.get.return_value = suggestion
        override_deps(app, db=db)

        with PatchRBAC():
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
                r = await ac.delete("/api/v1/managers/suggestions/8001")
        assert r.status_code == 200
        db.delete.assert_called_once_with(suggestion)


# ═══════════════════════════════════════════
# Task 4: Role 更新+删除
# ═══════════════════════════════════════════

def _role(rid=9001, is_system=False, tenant_id=TENANT_ID):
    r = MagicMock()
    r.id = rid
    r.tenant_id = tenant_id
    r.name = "自定义角色"
    r.code = "custom_role"
    r.description = None
    r.is_system = is_system
    r.parent_role_id = None
    r.permissions = []
    return r


class TestRoleUpdate:
    def _make_app(self):
        from app.api.endpoints.rbac import router
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/rbac")
        return app

    @pytest.mark.asyncio
    async def test_update_custom_role(self):
        app = self._make_app()
        role = _role()
        db = AsyncMock()
        db.get.return_value = role
        # check_org_admin 内部 db.execute(select(Role.code)) 需要同步 fetchall
        db.execute.return_value = MockScalarResult(items=[("admin",)])
        override_deps(app, db=db)

        with PatchRBAC():
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
                r = await ac.put("/api/v1/rbac/roles/9001", json={"name": "新角色名"})
        assert r.status_code == 200, f"实际: {r.status_code}, {r.text}"
        assert role.name == "新角色名"

    @pytest.mark.asyncio
    async def test_cannot_update_system_role(self):
        app = self._make_app()
        role = _role(is_system=True)
        db = AsyncMock()
        db.get.return_value = role
        db.execute.return_value = MockScalarResult(items=[("admin",)])
        override_deps(app, db=db)

        with PatchRBAC():
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
                r = await ac.put("/api/v1/rbac/roles/9001", json={"name": "hack"})
        assert r.status_code == 403


class TestRoleDelete:
    def _make_app(self):
        from app.api.endpoints.rbac import router
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/rbac")
        return app

    @pytest.mark.asyncio
    async def test_delete_custom_role(self):
        app = self._make_app()
        role = _role()
        db = AsyncMock()
        db.get.return_value = role
        # side_effect: 第1个 execute 给 check_org_admin，第2个给业务逻辑
        db.execute.side_effect = [
            MockScalarResult(items=[("admin",)]),  # check_org_admin: Role.code
            MockScalarResult(items=[]),             # 业务: 检查绑定用户
        ]
        override_deps(app, db=db)

        with PatchRBAC():
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
                r = await ac.delete("/api/v1/rbac/roles/9001")
        assert r.status_code == 200, f"实际: {r.status_code}, {r.text}"
        db.delete.assert_called_once_with(role)

    @pytest.mark.asyncio
    async def test_cannot_delete_system_role(self):
        app = self._make_app()
        role = _role(is_system=True)
        db = AsyncMock()
        db.get.return_value = role
        db.execute.return_value = MockScalarResult(items=[("admin",)])
        override_deps(app, db=db)

        with PatchRBAC():
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
                r = await ac.delete("/api/v1/rbac/roles/9001")
        assert r.status_code == 403
