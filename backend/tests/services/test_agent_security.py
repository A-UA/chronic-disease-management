"""SecurityContext 单元测试"""
import pytest
from app.modules.agent.security import SecurityContext


class TestSecurityContext:
    def test_immutable(self):
        ctx = SecurityContext(tenant_id=1, org_id=2, user_id=3)
        with pytest.raises(AttributeError):
            ctx.tenant_id = 999

    def test_has_permission(self):
        ctx = SecurityContext(
            tenant_id=1, org_id=2, user_id=3,
            permissions=frozenset({"patient:read"}),
        )
        assert ctx.has_permission("patient:read") is True
        assert ctx.has_permission("patient:delete") is False

    def test_require_permission_raises(self):
        ctx = SecurityContext(
            tenant_id=1, org_id=2, user_id=3, permissions=frozenset(),
        )
        with pytest.raises(PermissionError, match="缺少权限"):
            ctx.require_permission("patient:read")

    def test_require_permission_passes(self):
        ctx = SecurityContext(
            tenant_id=1, org_id=2, user_id=3,
            permissions=frozenset({"patient:read"}),
        )
        ctx.require_permission("patient:read")
