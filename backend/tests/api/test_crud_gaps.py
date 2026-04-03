"""CRUD 补全 TDD 测试

覆盖 7 个模块共 13 个缺失操作:
- Task1: ManagerProfile C/U/D
- Task2: PatientProfile C/D
- Task3: ManagementSuggestion U/D
- Task4: KnowledgeBase U
- Task5: HealthMetric U
- Task6: Role U/D
- Task7: User 信息编辑
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from app.api.deps import get_current_user, get_current_org, get_db, get_current_org_user


# ── 公用 Mock 工具 ──

def _dummy_user(uid=1001):
    u = MagicMock()
    u.id = uid
    u.email = "test@example.com"
    u.name = "测试用户"
    return u


def _mock_org_user():
    ou = MagicMock()
    ou.user_type = "staff"
    ou.org_id = 2001
    ou.user_id = 1001
    role = MagicMock()
    role.id = 1
    ou.rbac_roles = [role]
    return ou


class DummyResult:
    """简易 DB 查询结果 mock"""
    def __init__(self, items=None):
        self._items = items or []

    def scalar_one_or_none(self):
        return self._items[0] if self._items else None

    def scalars(self):
        m = MagicMock()
        m.all.return_value = self._items
        return m


def _async_override(app, db, uid=1001, org_id=2001):
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


# ═══════════════════════════════════════════
# Task 1: ManagerProfile CRUD (P0)
# ═══════════════════════════════════════════

class TestManagerProfileCreate:
    def _make_app(self):
        from app.api.endpoints.managers import router
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/managers")
        return app

    @pytest.mark.asyncio
    @patch("app.api.deps.RBACService.get_effective_permissions",
           new_callable=AsyncMock, return_value={"org_member:manage"})
    async def test_create_manager_profile(self, mock_perms):
        """创建管理师档案应成功"""
        app = self._make_app()
        target_user = MagicMock()
        target_user.id = 1002

        db = AsyncMock()
        db.execute.side_effect = [
            DummyResult([target_user]),   # 查用户存在
            DummyResult([]),              # 查无重复档案
        ]
        db.refresh = AsyncMock()

        _async_override(app, db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post("/api/v1/managers/profiles", json={
                "user_id": 1002,
                "title": "主任管理师",
                "bio": "10年慢病管理经验",
            })

        assert resp.status_code == 200, f"实际: {resp.status_code}, {resp.text}"
        db.add.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.api.deps.RBACService.get_effective_permissions",
           new_callable=AsyncMock, return_value={"org_member:manage"})
    async def test_create_duplicate_manager(self, mock_perms):
        """重复创建同一用户的管理师档案应返回409"""
        app = self._make_app()
        target_user = MagicMock()
        target_user.id = 1002
        existing = MagicMock()

        db = AsyncMock()
        db.execute.side_effect = [
            DummyResult([target_user]),
            DummyResult([existing]),       # 查到已有档案
        ]

        _async_override(app, db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post("/api/v1/managers/profiles", json={
                "user_id": 1002,
                "title": "管理师",
            })

        assert resp.status_code == 409


class TestManagerProfileUpdate:
    def _make_app(self):
        from app.api.endpoints.managers import router
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/managers")
        return app

    @pytest.mark.asyncio
    @patch("app.api.deps.RBACService.get_effective_permissions",
           new_callable=AsyncMock, return_value={"org_member:manage"})
    async def test_update_manager_title(self, mock_perms):
        """更新管理师职称应成功"""
        app = self._make_app()
        profile = MagicMock()
        profile.id = 3001
        profile.user_id = 1002
        profile.org_id = 2001
        profile.title = "旧职称"
        profile.bio = "旧简介"
        profile.is_active = True

        db = AsyncMock()
        db.get.return_value = profile

        _async_override(app, db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.put("/api/v1/managers/profiles/3001",
                                json={"title": "高级管理师"})

        assert resp.status_code == 200, f"实际: {resp.status_code}, {resp.text}"
        assert profile.title == "高级管理师"

    @pytest.mark.asyncio
    @patch("app.api.deps.RBACService.get_effective_permissions",
           new_callable=AsyncMock, return_value={"org_member:manage"})
    async def test_update_nonexistent_profile(self, mock_perms):
        """更新不存在的档案应返回404"""
        app = self._make_app()
        db = AsyncMock()
        db.get.return_value = None

        _async_override(app, db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.put("/api/v1/managers/profiles/99999",
                                json={"title": "不存在"})

        assert resp.status_code == 404


class TestManagerProfileDelete:
    def _make_app(self):
        from app.api.endpoints.managers import router
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/managers")
        return app

    @pytest.mark.asyncio
    @patch("app.api.deps.RBACService.get_effective_permissions",
           new_callable=AsyncMock, return_value={"org_member:manage"})
    async def test_deactivate_manager(self, mock_perms):
        """停用管理师档案应将 is_active 设为 False"""
        app = self._make_app()
        profile = MagicMock()
        profile.id = 3001
        profile.org_id = 2001
        profile.is_active = True

        db = AsyncMock()
        db.get.return_value = profile

        _async_override(app, db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.delete("/api/v1/managers/profiles/3001")

        assert resp.status_code == 200
        assert profile.is_active == False


# ═══════════════════════════════════════════
# Task 2: PatientProfile 创建+删除 (P0)
# ═══════════════════════════════════════════

class TestPatientProfileCreate:
    def _make_app(self):
        from app.api.endpoints.patients import router
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/patients")
        return app

    @pytest.mark.asyncio
    @patch("app.api.deps.RBACService.get_effective_permissions",
           new_callable=AsyncMock, return_value={"patient:create"})
    async def test_admin_create_patient(self, mock_perms):
        """管理员为用户创建患者档案应成功"""
        app = self._make_app()
        target_user = MagicMock()
        target_user.id = 1003

        db = AsyncMock()
        db.execute.side_effect = [
            DummyResult([target_user]),  # 用户存在
            DummyResult([]),             # 无重复
        ]
        db.refresh = AsyncMock()

        _async_override(app, db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post("/api/v1/patients/create", json={
                "user_id": 1003,
                "real_name": "张三",
                "gender": "male",
            })

        assert resp.status_code == 200, f"实际: {resp.status_code}, {resp.text}"
        db.add.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.api.deps.RBACService.get_effective_permissions",
           new_callable=AsyncMock, return_value={"patient:create"})
    async def test_create_duplicate_patient(self, mock_perms):
        """重复创建应返回 409"""
        app = self._make_app()
        target_user = MagicMock()
        target_user.id = 1003
        existing = MagicMock()

        db = AsyncMock()
        db.execute.side_effect = [
            DummyResult([target_user]),
            DummyResult([existing]),
        ]

        _async_override(app, db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post("/api/v1/patients/create", json={
                "user_id": 1003,
                "real_name": "张三",
            })

        assert resp.status_code == 409


class TestPatientProfileDelete:
    def _make_app(self):
        from app.api.endpoints.patients import router
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/patients")
        return app

    @pytest.mark.asyncio
    @patch("app.api.deps.RBACService.get_effective_permissions",
           new_callable=AsyncMock, return_value={"patient:delete"})
    async def test_delete_patient_profile(self, mock_perms):
        """管理员删除患者档案应成功"""
        app = self._make_app()
        profile = MagicMock()
        profile.id = 4001
        profile.org_id = 2001

        db = AsyncMock()
        db.get.return_value = profile

        _async_override(app, db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.delete("/api/v1/patients/4001")

        assert resp.status_code == 200
        db.delete.assert_called_once_with(profile)

    @pytest.mark.asyncio
    @patch("app.api.deps.RBACService.get_effective_permissions",
           new_callable=AsyncMock, return_value={"patient:delete"})
    async def test_delete_nonexistent_patient(self, mock_perms):
        """删除不存在的患者应返回 404"""
        app = self._make_app()
        db = AsyncMock()
        db.get.return_value = None

        _async_override(app, db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.delete("/api/v1/patients/99999")

        assert resp.status_code == 404


# ═══════════════════════════════════════════
# Task 3: ManagementSuggestion 更新+删除 (P0)
# ═══════════════════════════════════════════

class TestSuggestionUpdate:
    def _make_app(self):
        from app.api.endpoints.managers import router
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/managers")
        return app

    @pytest.mark.asyncio
    @patch("app.api.deps.RBACService.get_effective_permissions",
           new_callable=AsyncMock, return_value={"suggestion:create"})
    async def test_update_own_suggestion(self, mock_perms):
        """管理师修改自己发出的建议应成功"""
        app = self._make_app()
        suggestion = MagicMock()
        suggestion.id = 8001
        suggestion.manager_id = 1001  # 与 _dummy_user 的 id 一致
        suggestion.content = "旧建议"
        suggestion.suggestion_type = "general"
        suggestion.patient_id = 4001
        suggestion.org_id = 2001
        suggestion.created_at = "2026-04-01T00:00:00"

        db = AsyncMock()
        db.get.return_value = suggestion

        _async_override(app, db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.put("/api/v1/managers/suggestions/8001",
                                json={"content": "更新后的建议"})

        assert resp.status_code == 200, f"实际: {resp.status_code}, {resp.text}"
        assert suggestion.content == "更新后的建议"

    @pytest.mark.asyncio
    @patch("app.api.deps.RBACService.get_effective_permissions",
           new_callable=AsyncMock, return_value={"suggestion:create"})
    async def test_cannot_update_others_suggestion(self, mock_perms):
        """不能修改别人的建议应返回 403"""
        app = self._make_app()
        suggestion = MagicMock()
        suggestion.id = 8002
        suggestion.manager_id = 9999  # 不是当前用户
        suggestion.org_id = 2001

        db = AsyncMock()
        db.get.return_value = suggestion

        _async_override(app, db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.put("/api/v1/managers/suggestions/8002",
                                json={"content": "恶意修改"})

        assert resp.status_code == 403


class TestSuggestionDelete:
    def _make_app(self):
        from app.api.endpoints.managers import router
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/managers")
        return app

    @pytest.mark.asyncio
    @patch("app.api.deps.RBACService.get_effective_permissions",
           new_callable=AsyncMock, return_value={"suggestion:create"})
    async def test_delete_own_suggestion(self, mock_perms):
        """管理师撤回自己的建议应成功"""
        app = self._make_app()
        suggestion = MagicMock()
        suggestion.id = 8001
        suggestion.manager_id = 1001
        suggestion.org_id = 2001

        db = AsyncMock()
        db.get.return_value = suggestion

        _async_override(app, db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.delete("/api/v1/managers/suggestions/8001")

        assert resp.status_code == 200
        db.delete.assert_called_once_with(suggestion)


# ═══════════════════════════════════════════
# Task 4: KnowledgeBase 更新 (P1)
# ═══════════════════════════════════════════

class TestKnowledgeBaseUpdate:
    def _make_app(self):
        from app.api.endpoints.knowledge_bases import router
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/kb")
        return app

    @pytest.mark.asyncio
    async def test_update_kb_name(self):
        """更新知识库名称和描述应成功"""
        app = self._make_app()
        kb = MagicMock()
        kb.id = 5001
        kb.org_id = 2001
        kb.name = "旧名称"
        kb.description = "旧描述"
        kb.created_at = "2026-01-01T00:00:00"

        db = AsyncMock()
        db.get.return_value = kb

        _async_override(app, db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.put("/api/v1/kb/5001",
                                json={"name": "新名称", "description": "新描述"})

        assert resp.status_code == 200, f"实际: {resp.status_code}, {resp.text}"
        assert kb.name == "新名称"
        assert kb.description == "新描述"


# ═══════════════════════════════════════════
# Task 5: HealthMetric 更新 (P1)
# ═══════════════════════════════════════════

class TestHealthMetricUpdate:
    def _make_app(self):
        from app.api.endpoints.health_metrics import router
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/health-metrics")
        return app

    @pytest.mark.asyncio
    async def test_update_metric_value(self):
        """修正录入错误的指标值应成功"""
        app = self._make_app()
        metric = MagicMock()
        metric.id = 7001
        metric.recorded_by = 1001
        metric.org_id = 2001
        metric.value = 130.0

        db = AsyncMock()
        db.get.return_value = metric

        _async_override(app, db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.put("/api/v1/health-metrics/7001",
                                json={"value": 125.0})

        assert resp.status_code == 200, f"实际: {resp.status_code}, {resp.text}"
        assert metric.value == 125.0

    @pytest.mark.asyncio
    async def test_cannot_update_others_metric(self):
        """不能修改别人的记录应返回 403"""
        app = self._make_app()
        metric = MagicMock()
        metric.id = 7002
        metric.recorded_by = 9999  # 不是当前用户
        metric.org_id = 2001

        db = AsyncMock()
        db.get.return_value = metric

        _async_override(app, db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.put("/api/v1/health-metrics/7002",
                                json={"value": 999.0})

        assert resp.status_code == 403


# ═══════════════════════════════════════════
# Task 6: Role 更新+删除 (P1)
# ═══════════════════════════════════════════

class DummyFetchResult:
    """模拟 db.execute() 返回 fetchall() 的结果"""
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows

    def scalars(self):
        m = MagicMock()
        m.all.return_value = [r[0] if isinstance(r, tuple) else r for r in self._rows]
        m.first.return_value = self._rows[0] if self._rows else None
        return m


class TestRoleUpdate:
    def _make_app(self):
        from app.api.endpoints.rbac import router
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/rbac")
        return app

    @pytest.mark.asyncio
    @patch("app.services.rbac.RBACService.get_all_role_ids",
           new_callable=AsyncMock, return_value={1})
    @patch("app.api.deps.RBACService.get_effective_permissions",
           new_callable=AsyncMock, return_value={"org:manage"})
    async def test_update_custom_role(self, mock_perms, mock_role_ids):
        """更新自定义角色名称应成功"""
        app = self._make_app()
        role = MagicMock()
        role.id = 9001
        role.org_id = 2001
        role.name = "旧角色名"
        role.code = "custom_role"
        role.description = None
        role.is_system = False
        role.parent_role_id = None
        role.permissions = []

        db = AsyncMock()
        # check_org_admin 内部查角色代码 → 返回 [("admin",)]
        # update_role 内部用 db.get → 返回 role
        db.execute.return_value = DummyFetchResult([("admin",)])
        db.get.return_value = role

        _async_override(app, db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.put("/api/v1/rbac/roles/9001",
                                json={"name": "新角色名"})

        assert resp.status_code == 200, f"实际: {resp.status_code}, {resp.text}"
        assert role.name == "新角色名"

    @pytest.mark.asyncio
    @patch("app.services.rbac.RBACService.get_all_role_ids",
           new_callable=AsyncMock, return_value={1})
    @patch("app.api.deps.RBACService.get_effective_permissions",
           new_callable=AsyncMock, return_value={"org:manage"})
    async def test_cannot_update_system_role(self, mock_perms, mock_role_ids):
        """不能修改系统角色应返回 403"""
        app = self._make_app()
        role = MagicMock()
        role.id = 1
        role.org_id = 2001
        role.is_system = True

        db = AsyncMock()
        db.execute.return_value = DummyFetchResult([("admin",)])
        db.get.return_value = role

        _async_override(app, db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.put("/api/v1/rbac/roles/1",
                                json={"name": "hack"})

        assert resp.status_code == 403


class TestRoleDelete:
    def _make_app(self):
        from app.api.endpoints.rbac import router
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/rbac")
        return app

    @pytest.mark.asyncio
    @patch("app.services.rbac.RBACService.get_all_role_ids",
           new_callable=AsyncMock, return_value={1})
    @patch("app.api.deps.RBACService.get_effective_permissions",
           new_callable=AsyncMock, return_value={"org:manage"})
    async def test_delete_custom_role(self, mock_perms, mock_role_ids):
        """删除自定义角色应成功"""
        app = self._make_app()
        role = MagicMock()
        role.id = 9001
        role.org_id = 2001
        role.is_system = False

        db = AsyncMock()
        # check_org_admin: 角色代码查询
        # delete_role: db.get → role, db.execute (检查绑定用户) → 空
        db.execute.side_effect = [
            DummyFetchResult([("admin",)]),    # check_org_admin 角色代码
            DummyFetchResult([]),               # 检查绑定用户 → 无绑定
        ]
        db.get.return_value = role

        _async_override(app, db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.delete("/api/v1/rbac/roles/9001")

        assert resp.status_code == 200, f"实际: {resp.status_code}, {resp.text}"
        db.delete.assert_called_once_with(role)

    @pytest.mark.asyncio
    @patch("app.services.rbac.RBACService.get_all_role_ids",
           new_callable=AsyncMock, return_value={1})
    @patch("app.api.deps.RBACService.get_effective_permissions",
           new_callable=AsyncMock, return_value={"org:manage"})
    async def test_cannot_delete_system_role(self, mock_perms, mock_role_ids):
        """不能删除系统角色应返回 403"""
        app = self._make_app()
        role = MagicMock()
        role.id = 1
        role.org_id = 2001
        role.is_system = True

        db = AsyncMock()
        db.execute.return_value = DummyFetchResult([("admin",)])
        db.get.return_value = role

        _async_override(app, db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.delete("/api/v1/rbac/roles/1")

        assert resp.status_code == 403


# ═══════════════════════════════════════════
# Task 7: User 信息编辑 (P2)
# ═══════════════════════════════════════════

class TestUserProfileUpdate:
    def _make_app(self):
        from app.api.endpoints.auth import router
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/auth")
        return app

    @pytest.mark.asyncio
    async def test_update_my_name(self):
        """用户修改自己的姓名应成功"""
        app = self._make_app()
        db = AsyncMock()

        _async_override(app, db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.put("/api/v1/auth/me/profile",
                                json={"name": "新姓名"})

        assert resp.status_code == 200, f"实际: {resp.status_code}, {resp.text}"
