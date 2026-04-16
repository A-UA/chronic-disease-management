from __future__ import annotations

from dataclasses import dataclass, field

# Removed SQLAlchemy dependency

@dataclass(frozen=True, slots=True)
class SecurityContext:
    """Agent 执行所需的安全上下文 — 由 FastAPI DI 层构建

    Attributes:
        tenant_id: 租户 ID（RLS 隔离键）
        org_id: 部门 ID
        user_id: 当前用户 ID
        roles: 用户角色列表
        permissions: 用户有效权限集合（含角色继承）
        auth_headers: 用于向 Gateway 发起安全 HTTP 请求的请求头（如 X-Identity-Base64 或 JWT Token）
    """

    tenant_id: int
    org_id: int
    user_id: int
    roles: tuple[str, ...] = ()
    permissions: frozenset[str] = field(default_factory=frozenset)
    auth_headers: dict[str, str] = field(default_factory=dict)

    def has_permission(self, perm_code: str) -> bool:
        """检查是否拥有指定权限"""
        return perm_code in self.permissions

    def require_permission(self, perm_code: str) -> None:
        """要求指定权限，无则抛 PermissionError"""
        if perm_code not in self.permissions:
            raise PermissionError(f"缺少权限: {perm_code}")
