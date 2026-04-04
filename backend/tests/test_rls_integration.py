"""B12: RLS 隔离集成测试

使用 Mock 验证 inject_rls_context 依赖正确设置 PostgreSQL 会话变量。
真实 RLS 隔离需要在实际 PostgreSQL 上运行。
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch


class TestInjectRLSContext:
    """验证 inject_rls_context 依赖行为"""

    @pytest.mark.asyncio
    async def test_sets_tenant_id(self):
        """应正确设置 app.current_tenant_id"""
        from app.api.deps import inject_rls_context

        db = AsyncMock()
        db.execute = AsyncMock()

        # Mock JWT 解析出的 tenant_id
        with patch("app.api.deps.get_current_tenant_id", return_value=1001), \
             patch("app.api.deps.get_db", return_value=db):
            # 直接调用依赖函数
            result = await inject_rls_context(tenant_id=1001, db=db)

        assert result == 1001
        # 验证确实调用了 set_config
        call_args_list = db.execute.call_args_list
        assert len(call_args_list) >= 1
        # 第一次调用应设置 tenant_id
        first_call = str(call_args_list[0])
        assert "current_tenant_id" in first_call or "1001" in first_call


class TestEffectiveOrgId:
    """验证 get_effective_org_id 行为"""

    @pytest.mark.asyncio
    async def test_admin_gets_none(self):
        """admin/owner 角色应返回 None（租户级访问）"""
        from app.api.deps import get_effective_org_id
        result = await get_effective_org_id(org_id=2001, roles=["admin"])
        assert result is None

    @pytest.mark.asyncio
    async def test_owner_gets_none(self):
        from app.api.deps import get_effective_org_id
        result = await get_effective_org_id(org_id=2001, roles=["owner"])
        assert result is None

    @pytest.mark.asyncio
    async def test_staff_gets_org_id(self):
        """staff 角色应返回 org_id（部门级访问）"""
        from app.api.deps import get_effective_org_id
        result = await get_effective_org_id(org_id=2001, roles=["staff"])
        assert result == 2001

    @pytest.mark.asyncio
    async def test_manager_gets_org_id(self):
        from app.api.deps import get_effective_org_id
        result = await get_effective_org_id(org_id=2001, roles=["manager"])
        assert result == 2001


class TestRLSPolicyMigration:
    """验证 RLS 策略 SQL 覆盖的表"""

    def _load_module(self):
        import importlib.util, os
        path = os.path.join(
            os.path.dirname(__file__), "..", "alembic", "versions",
            "rls_policies_001_deploy_rls.py"
        )
        spec = importlib.util.spec_from_file_location("rls_migration", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_all_tenant_tables_have_rls(self):
        """所有关键业务表都应有 RLS 策略"""
        mod = self._load_module()
        all_rls_tables = set(mod.TENANT_TABLES) | set(mod.NULLABLE_TENANT_TABLES) | {mod.FAMILY_LINK_TABLE}

        # 验证关键表
        critical_tables = [
            "patient_profiles", "health_metrics", "conversations",
            "knowledge_bases", "documents", "audit_logs",
        ]
        for table in critical_tables:
            assert table in all_rls_tables, f"关键表 {table} 缺少 RLS 保护"

    def test_system_tables_excluded(self):
        """全局表不应启用 RLS"""
        mod = self._load_module()
        all_rls = set(mod.TENANT_TABLES) | set(mod.NULLABLE_TENANT_TABLES) | {mod.FAMILY_LINK_TABLE}

        # 这些全局表不应在 RLS 列表中
        global_tables = ["users", "permissions", "role_permissions"]
        for table in global_tables:
            assert table not in all_rls, f"全局表 {table} 不应启用 RLS"
