from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True, slots=True)
class SecurityContext:
    """Agent 执行所需的安全上下文 — 由 FastAPI DI 层构建

    Attributes:
        tenant_id: 租户 ID（RLS 隔离键）
        org_id: 部门 ID
        user_id: 当前用户 ID
        roles: 用户角色列表
        permissions: 用户有效权限集合（含角色继承）
        db: 已注入 RLS 上下文的 AsyncSession（set_config 已执行）
    """

    tenant_id: int
    org_id: int
    user_id: int
    roles: tuple[str, ...] = ()
    permissions: frozenset[str] = field(default_factory=frozenset)
    db: AsyncSession | None = None

    def has_permission(self, perm_code: str) -> bool:
        """检查是否拥有指定权限"""
        return perm_code in self.permissions

    def require_permission(self, perm_code: str) -> None:
        """要求指定权限，无则抛 PermissionError"""
        if perm_code not in self.permissions:
            raise PermissionError(f"缺少权限: {perm_code}")
