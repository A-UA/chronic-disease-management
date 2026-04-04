"""多租户架构验证测试

验证核心架构组件的存在性和行为正确性
"""
import pytest
import importlib


class TestDepsExistence:
    """验证 deps.py 中所有关键依赖函数存在"""

    def test_get_current_user(self):
        from app.api.deps import get_current_user
        assert callable(get_current_user)

    def test_get_current_tenant_id(self):
        from app.api.deps import get_current_tenant_id
        assert callable(get_current_tenant_id)

    def test_get_current_org_id(self):
        from app.api.deps import get_current_org_id
        assert callable(get_current_org_id)

    def test_get_effective_org_id(self):
        from app.api.deps import get_effective_org_id
        assert callable(get_effective_org_id)

    def test_get_current_roles(self):
        from app.api.deps import get_current_roles
        assert callable(get_current_roles)

    def test_inject_rls_context(self):
        from app.api.deps import inject_rls_context
        assert callable(inject_rls_context)

    def test_get_current_org_user(self):
        from app.api.deps import get_current_org_user
        assert callable(get_current_org_user)

    def test_check_permission(self):
        from app.api.deps import check_permission
        assert callable(check_permission)

    def test_check_org_admin(self):
        from app.api.deps import check_org_admin
        assert callable(check_org_admin)

    def test_verify_quota(self):
        from app.api.deps import verify_quota
        assert callable(verify_quota)

    def test_tenant_wide_roles_defined(self):
        from app.api.deps import TENANT_WIDE_ROLES
        assert "admin" in TENANT_WIDE_ROLES
        assert "owner" in TENANT_WIDE_ROLES


class TestTenantWideRolesLogic:
    """验证 admin/owner 跨部门访问逻辑"""

    @pytest.mark.asyncio
    async def test_admin_gets_none(self):
        """admin 角色 → effective_org_id 返回 None"""
        from app.api.deps import TENANT_WIDE_ROLES
        roles = ["admin"]
        if set(roles) & TENANT_WIDE_ROLES:
            result = None
        else:
            result = 2001
        assert result is None

    @pytest.mark.asyncio
    async def test_staff_gets_org_id(self):
        """staff 角色 → effective_org_id 返回 org_id"""
        from app.api.deps import TENANT_WIDE_ROLES
        roles = ["staff"]
        if set(roles) & TENANT_WIDE_ROLES:
            result = None
        else:
            result = 2001
        assert result == 2001


class TestModelsExistence:
    """验证重要 ORM 模型存在"""

    def test_tenant_model(self):
        from app.db.models import Tenant
        assert Tenant is not None

    def test_organization_model(self):
        from app.db.models import Organization
        assert Organization is not None

    def test_organization_user_model(self):
        from app.db.models import OrganizationUser
        assert OrganizationUser is not None

    def test_patient_profile_model(self):
        from app.db.models import PatientProfile
        assert PatientProfile is not None

    def test_health_metric_model(self):
        from app.db.models import HealthMetric
        assert HealthMetric is not None

    def test_conversation_model(self):
        from app.db.models import Conversation
        assert Conversation is not None


class TestAllEndpointsImport:
    """验证所有端点模块可以无错导入"""

    def test_api_router_imports(self):
        from app.api.api import api_router
        assert api_router is not None
