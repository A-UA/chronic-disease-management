"""RLS 策略迁移脚本验证测试

验证：
1. 迁移脚本可正常导入且格式合规
2. 所有需要 RLS 的表都被覆盖
3. upgrade/downgrade 函数存在
4. 家属穿透策略已包含
"""
import pytest
import importlib


# 预期需要 RLS 的业务表
EXPECTED_TENANT_TABLES = [
    "organizations",
    "organization_users",
    "organization_user_roles",
    "organization_invitations",
    "patient_profiles",
    "health_metrics",
    "manager_profiles",
    "patient_manager_assignments",
    "management_suggestions",
    "knowledge_bases",
    "documents",
    "chunks",
    "conversations",
    "messages",
    "usage_logs",
    "audit_logs",
    "api_keys",
]


class TestRLSMigrationScript:
    """验证 RLS 迁移脚本的完整性"""

    def _load_module(self):
        """动态加载迁移脚本模块"""
        import importlib.util
        import os
        path = os.path.join(
            os.path.dirname(__file__), "..", "alembic", "versions",
            "rls_policies_001_deploy_rls.py"
        )
        spec = importlib.util.spec_from_file_location("rls_migration", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_module_loads(self):
        mod = self._load_module()
        assert mod is not None

    def test_revision_id(self):
        mod = self._load_module()
        assert mod.revision == "rls_policies_001"
        assert mod.down_revision == "d08f011b680f"

    def test_upgrade_function_exists(self):
        mod = self._load_module()
        assert callable(mod.upgrade)

    def test_downgrade_function_exists(self):
        mod = self._load_module()
        assert callable(mod.downgrade)

    def test_all_tenant_tables_covered(self):
        """所有含 tenant_id NOT NULL 的表必须被 RLS 覆盖"""
        mod = self._load_module()
        for table in EXPECTED_TENANT_TABLES:
            assert table in mod.TENANT_TABLES, \
                f"表 {table} 未包含在 RLS TENANT_TABLES 列表中"

    def test_family_link_table_defined(self):
        """家属穿透表必须单独处理"""
        mod = self._load_module()
        assert mod.FAMILY_LINK_TABLE == "patient_family_links"

    def test_nullable_tenant_tables(self):
        """角色表等 tenant_id 可为 NULL 的表需特殊策略"""
        mod = self._load_module()
        assert "roles" in mod.NULLABLE_TENANT_TABLES
        assert "rbac_role_constraints" in mod.NULLABLE_TENANT_TABLES

    def test_no_duplicate_tables(self):
        """各表列表不应有重叠"""
        mod = self._load_module()
        all_tables = (
            set(mod.TENANT_TABLES)
            | set(mod.NULLABLE_TENANT_TABLES)
            | {mod.FAMILY_LINK_TABLE}
        )
        total = (
            len(mod.TENANT_TABLES)
            + len(mod.NULLABLE_TENANT_TABLES)
            + 1
        )
        assert len(all_tables) == total, "存在重复的表名"
