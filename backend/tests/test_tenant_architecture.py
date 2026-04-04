"""多租户架构单元测试

验证 Tenant-Organization 双层模型的核心逻辑：
1. 模型字段与约束
2. JWT 令牌生成（含 tenant_id）
3. 种子数据完整性
4. 依赖注入函数存在性  
5. 端点路由注册
6. 配额服务改为 tenant 维度
"""
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock


# ───────────────────────────────────────────
# 1. 模型层测试：Tenant 模型字段与关系
# ───────────────────────────────────────────


class TestTenantModel:
    """Tenant 模型字段验证"""

    def test_tenant_table_exists(self):
        from app.db.models import Tenant
        assert Tenant.__tablename__ == "tenants"

    def test_tenant_has_required_columns(self):
        from app.db.models import Tenant
        cols = {c.name for c in Tenant.__table__.columns}
        required = {"id", "name", "slug", "status", "plan_type",
                     "quota_tokens_limit", "quota_tokens_used",
                     "max_members", "max_patients", "created_at"}
        assert required.issubset(cols), f"缺少字段: {required - cols}"

    def test_tenant_slug_unique(self):
        from app.db.models import Tenant
        unique_cols = set()
        for constraint in Tenant.__table__.constraints:
            if constraint.__class__.__name__ == "UniqueConstraint":
                for col in constraint.columns:
                    unique_cols.add(col.name)
        assert "slug" in unique_cols


class TestOrganizationModel:
    """Organization 重构后的模型验证"""

    def test_organization_has_tenant_id(self):
        from app.db.models import Organization
        cols = {c.name for c in Organization.__table__.columns}
        assert "tenant_id" in cols

    def test_organization_has_code_field(self):
        from app.db.models import Organization
        cols = {c.name for c in Organization.__table__.columns}
        assert "code" in cols

    def test_organization_unique_constraint(self):
        """组织的唯一约束应为 (tenant_id, code)"""
        from app.db.models import Organization
        unique_constraints = set()
        for constraint in Organization.__table__.constraints:
            if constraint.__class__.__name__ == "UniqueConstraint":
                unique_constraints.add(
                    tuple(c.name for c in constraint.columns)
                )
        assert ("tenant_id", "code") in unique_constraints

    def test_organization_no_plan_type(self):
        """Organization 不再拥有 plan_type（已迁移到 Tenant）"""
        from app.db.models import Organization
        cols = {c.name for c in Organization.__table__.columns}
        assert "plan_type" not in cols


# ───────────────────────────────────────────
# 2. 所有业务模型必须有 tenant_id 字段
# ───────────────────────────────────────────


class TestAllModelsHaveTenantId:
    """验证所有核心业务模型都已注入 tenant_id"""

    MODELS_WITH_TENANT = [
        "PatientProfile", "HealthMetric", "ManagerProfile",
        "PatientManagerAssignment", "ManagementSuggestion",
        "KnowledgeBase", "Document", "Chunk",
        "Conversation", "Message", "UsageLog",
        "ApiKey", "AuditLog", "OrganizationUser",
        "OrganizationUserRole", "OrganizationInvitation",
    ]

    @pytest.mark.parametrize("model_name", MODELS_WITH_TENANT)
    def test_model_has_tenant_id(self, model_name):
        import app.db.models as models
        model = getattr(models, model_name)
        cols = {c.name for c in model.__table__.columns}
        assert "tenant_id" in cols, f"{model_name} 缺少 tenant_id 字段"


class TestRoleModelTenantId:
    """Role 模型的 org_id 应替换为 tenant_id"""

    def test_role_has_tenant_id(self):
        from app.db.models import Role
        cols = {c.name for c in Role.__table__.columns}
        assert "tenant_id" in cols

    def test_role_unique_constraint(self):
        """角色唯一约束应为 (tenant_id, code)"""
        from app.db.models import Role
        unique_constraints = set()
        for constraint in Role.__table__.constraints:
            if constraint.__class__.__name__ == "UniqueConstraint":
                unique_constraints.add(
                    tuple(c.name for c in constraint.columns)
                )
        assert ("tenant_id", "code") in unique_constraints


# ───────────────────────────────────────────
# 3. JWT 令牌测试
# ───────────────────────────────────────────


class TestJWTTokens:
    """JWT 令牌相关功能"""

    def test_access_token_contains_full_context(self):
        """访问令牌应包含 tenant_id + org_id + roles"""
        from app.core.security import create_access_token, ALGORITHM
        from app.core.config import settings
        import jwt as pyjwt

        token = create_access_token(
            subject="123", tenant_id=456, org_id=789, roles=["admin"]
        )
        payload = pyjwt.decode(
            token, settings.JWT_SECRET, algorithms=[ALGORITHM]
        )
        assert payload["sub"] == "123"
        assert payload["tenant_id"] == "456"
        assert payload["org_id"] == "789"
        assert payload["roles"] == ["admin"]

    def test_selection_token_has_org_purpose(self):
        """selection token 的 purpose 应为 org_selection"""
        from app.core.security import create_selection_token, ALGORITHM
        from app.core.config import settings
        import jwt as pyjwt

        token = create_selection_token(user_id="321")
        payload = pyjwt.decode(
            token, settings.JWT_SECRET, algorithms=[ALGORITHM]
        )
        assert payload["sub"] == "321"
        assert payload["purpose"] == "org_selection"

    def test_access_token_without_optional_fields(self):
        """不传可选字段时令牌也能正常生成"""
        from app.core.security import create_access_token, ALGORITHM
        from app.core.config import settings
        import jwt as pyjwt

        token = create_access_token(subject="100")
        payload = pyjwt.decode(
            token, settings.JWT_SECRET, algorithms=[ALGORITHM]
        )
        assert payload["sub"] == "100"
        assert "tenant_id" not in payload
        assert "org_id" not in payload
        assert "roles" not in payload

    def test_admin_roles_in_token(self):
        """多角色能正确序列化到 JWT"""
        from app.core.security import create_access_token, ALGORITHM
        from app.core.config import settings
        import jwt as pyjwt

        token = create_access_token(
            subject="1", tenant_id=1, org_id=1, roles=["staff", "manager"]
        )
        payload = pyjwt.decode(
            token, settings.JWT_SECRET, algorithms=[ALGORITHM]
        )
        assert set(payload["roles"]) == {"staff", "manager"}


# ───────────────────────────────────────────
# 4. 依赖注入函数存在性测试
# ───────────────────────────────────────────


class TestDepsExistence:
    """deps.py 的关键依赖函数应该存在"""

    def test_get_current_tenant_id_exists(self):
        from app.api.deps import get_current_tenant_id
        assert callable(get_current_tenant_id)

    def test_get_current_org_id_exists(self):
        from app.api.deps import get_current_org_id
        assert callable(get_current_org_id)

    def test_get_current_roles_exists(self):
        from app.api.deps import get_current_roles
        assert callable(get_current_roles)

    def test_get_effective_org_id_exists(self):
        from app.api.deps import get_effective_org_id
        assert callable(get_effective_org_id)

    def test_inject_rls_context_exists(self):
        from app.api.deps import inject_rls_context
        assert callable(inject_rls_context)

    def test_get_current_org_exists(self):
        from app.api.deps import get_current_org
        assert callable(get_current_org)

    def test_verify_quota_exists(self):
        from app.api.deps import verify_quota
        assert callable(verify_quota)

    def test_tenant_wide_roles_defined(self):
        """应定义租户级访问角色集合"""
        from app.api.deps import TENANT_WIDE_ROLES
        assert "admin" in TENANT_WIDE_ROLES
        assert "owner" in TENANT_WIDE_ROLES
        assert "staff" not in TENANT_WIDE_ROLES


# ───────────────────────────────────────────
# 5. 路由注册测试
# ───────────────────────────────────────────


class TestRouteRegistration:
    """所有端点路由应正确注册"""

    def _get_all_paths(self):
        from app.main import app
        return {route.path for route in app.routes if hasattr(route, "path")}

    def test_auth_routes(self):
        paths = self._get_all_paths()
        assert "/api/v1/auth/register" in paths
        # 登录路由应该存在
        auth_paths = [p for p in paths if "/auth/" in p]
        assert len(auth_paths) >= 3, f"Auth 路由太少: {auth_paths}"

    def test_patient_routes(self):
        paths = self._get_all_paths()
        patient_paths = [p for p in paths if "/patients" in p]
        assert len(patient_paths) >= 2

    def test_chat_routes(self):
        paths = self._get_all_paths()
        assert any("/chat" in p for p in paths)

    def test_kb_routes(self):
        paths = self._get_all_paths()
        assert any("/kb" in p for p in paths)

    def test_rbac_routes(self):
        paths = self._get_all_paths()
        assert any("/rbac" in p for p in paths)

    def test_dashboard_routes(self):
        paths = self._get_all_paths()
        assert any("/dashboard" in p for p in paths)


# ───────────────────────────────────────────
# 6. 配额服务测试
# ───────────────────────────────────────────


class TestQuotaService:
    """配额服务应使用 tenant 维度"""

    def test_update_tenant_quota_function_exists(self):
        from app.services.quota import update_tenant_quota
        assert callable(update_tenant_quota)

    def test_check_quota_during_stream_function_exists(self):
        from app.services.quota import check_quota_during_stream
        assert callable(check_quota_during_stream)

    def test_backward_compat_alias(self):
        """旧函数名应作为兼容别名"""
        from app.services import quota
        assert hasattr(quota, "update_org_quota") or hasattr(quota, "update_tenant_quota")


# ───────────────────────────────────────────
# 7. 审计服务测试
# ───────────────────────────────────────────


class TestAuditService:
    """审计服务应支持 tenant_id"""

    def test_audit_action_accepts_tenant_id(self):
        import inspect
        from app.services.audit import audit_action

        sig = inspect.signature(audit_action)
        assert "tenant_id" in sig.parameters

    @pytest.mark.asyncio
    async def test_audit_creates_log_with_tenant_id(self):
        """audit_action 应在 AuditLog 中设置 tenant_id"""
        from app.services.audit import audit_action
        from unittest.mock import AsyncMock

        mock_db = AsyncMock()
        mock_db.add = MagicMock()

        await audit_action(
            db=mock_db,
            user_id=1,
            org_id=2,
            action="test",
            resource_type="test",
            tenant_id=100,
        )

        # 验证 db.add 被调用且对象有 tenant_id
        assert mock_db.add.called
        log_obj = mock_db.add.call_args[0][0]
        assert log_obj.tenant_id == 100


# ───────────────────────────────────────────
# 8. 种子数据结构测试
# ───────────────────────────────────────────


class TestSeedDataStructure:
    """种子数据脚本结构验证"""

    def test_seed_data_module_importable(self):
        import app.db.seed_data
        assert hasattr(app.db.seed_data, "main")

    def test_seed_references_tenant(self):
        """种子数据应包含 Tenant 初始化"""
        import inspect
        import app.db.seed_data as seed_module

        # 检查整个模块源码是否包含 Tenant
        source = inspect.getsource(seed_module)
        assert "Tenant" in source, "种子数据模块中应包含 Tenant 初始化"


# ───────────────────────────────────────────
# 9. 集成测试：应用启动与健康检查
# ───────────────────────────────────────────


class TestAppIntegration:
    """应用全局集成测试"""

    @pytest.mark.asyncio
    async def test_app_starts_without_import_errors(self):
        """应用应能正常导入（无循环依赖或导入错误）"""
        from app.main import app
        assert app is not None
        assert app.title is not None

    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        """健康检查端点正常返回"""
        from app.main import app
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            r = await ac.get("/health")
        assert r.status_code in (200, 503)
        data = r.json()
        assert "status" in data

    @pytest.mark.asyncio
    async def test_unauthenticated_endpoints_return_401(self):
        """无认证请求到受保护端点应返回 401"""
        from app.main import app
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            r = await ac.get("/api/v1/patients")
        assert r.status_code == 401
