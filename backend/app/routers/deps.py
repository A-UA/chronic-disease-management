"""依赖注入：认证 → 租户/部门上下文（从 JWT） → RLS 注入 → 权限校验

JWT payload 结构：
{
    "sub": "user_id",
    "tenant_id": "从 org 反查",
    "org_id": "用户选中的部门",
    "roles": ["admin"],   // 用户在该部门的角色
    "exp": "..."
}

访问范围规则：
- admin / owner 角色 → tenant 级（org_id 过滤可选）
- staff / manager 角色 → department 级（强制 org_id 过滤）
"""

import hashlib
import hmac
import logging
from datetime import datetime, timezone
from typing import Annotated, TypeVar

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.base.config import settings
from app.base.database import get_db
from app.base.security import ALGORITHM
from app.models import (
    ApiKey,
    OrganizationUser,
    Role,
    Tenant,
    User,
)
from app.services.system.rbac import RBACService

logger = logging.getLogger(__name__)

# 可跨部门查看的角色
TENANT_WIDE_ROLES = {"admin", "owner"}

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login/access-token"
)


# ── 第 1 层：用户认证 ──


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme),
) -> User:
    """从 JWT 解析用户身份"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    user = await db.get(User, int(user_id))
    if user is None:
        raise credentials_exception

    # 注入 user_id 供 RLS 家属穿透使用
    await db.execute(
        text("SELECT set_config('app.current_user_id', :uid, true)"),
        {"uid": str(user.id)},
    )
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.deleted_at is not None:
        raise HTTPException(status_code=403, detail="User account has been disabled")
    return current_user


# ── 第 2 层：租户上下文（从 JWT 读取，零查询） ──


async def get_current_tenant_id(
    token: str = Depends(oauth2_scheme),
) -> int:
    """从 JWT payload 直接读取 tenant_id"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
        tenant_id = payload.get("tenant_id")
        if tenant_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Token does not contain tenant context. Please select an organization.",
            )
        return int(tenant_id)
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


# ── 第 3 层：部门上下文（从 JWT 读取，零查询） ──


async def get_current_org_id(
    token: str = Depends(oauth2_scheme),
) -> int:
    """从 JWT payload 直接读取 org_id"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
        org_id = payload.get("org_id")
        if org_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Token does not contain organization context.",
            )
        return int(org_id)
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


async def get_current_roles(
    token: str = Depends(oauth2_scheme),
) -> list[str]:
    """从 JWT payload 读取当前用户角色列表"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
        return payload.get("roles", [])
    except jwt.PyJWTError:
        return []


async def get_effective_org_id(
    roles: list[str] = Depends(get_current_roles),
    org_id: int = Depends(get_current_org_id),
) -> int | None:
    """根据角色决定是否进行部门过滤

    - admin/owner → 返回 None（租户级访问，不限部门）
    - staff/manager → 返回 org_id（严格限定本部门）
    """
    if set(roles) & TENANT_WIDE_ROLES:
        return None
    return org_id


# ── 第 4 层：RLS 上下文注入 ──


async def inject_rls_context(
    tenant_id: int = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> int:
    """将 tenant_id 注入 PostgreSQL 会话变量，用于 RLS"""
    await db.execute(
        text("SELECT set_config('app.current_tenant_id', :tid, true)"),
        {"tid": str(tenant_id)},
    )
    return tenant_id


# ── 第 5 层：OrganizationUser 上下文（需要 DB 查询，用于需要角色-权限细节的端点） ──


async def get_current_org_user(
    tenant_id: int = Depends(inject_rls_context),
    org_id: int = Depends(get_current_org_id),
    roles: list[str] = Depends(get_current_roles),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrganizationUser:
    """获取用户在当前部门的组织身份（含角色和权限）"""
    # 直接查本部门
    stmt = (
        select(OrganizationUser)
        .where(
            OrganizationUser.org_id == org_id,
            OrganizationUser.user_id == current_user.id,
        )
        .options(
            selectinload(OrganizationUser.rbac_roles).selectinload(Role.permissions)
        )
    )
    result = await db.execute(stmt)
    org_user = result.scalar_one_or_none()

    if org_user:
        return org_user

    # 不是直接成员但有 admin/owner 角色 → 构造穿透 OrgUser
    if set(roles) & TENANT_WIDE_ROLES:
        # 用用户在该租户下任一部门的角色来穿透
        stmt_any = (
            select(OrganizationUser)
            .where(
                OrganizationUser.tenant_id == tenant_id,
                OrganizationUser.user_id == current_user.id,
            )
            .options(selectinload(OrganizationUser.rbac_roles))
            .limit(1)
        )
        result_any = await db.execute(stmt_any)
        any_ou = result_any.scalar_one_or_none()
        if any_ou:
            return OrganizationUser(
                tenant_id=tenant_id,
                org_id=org_id,
                user_id=current_user.id,
                user_type=any_ou.user_type,
                rbac_roles=list(any_ou.rbac_roles),
            )

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Not a member of this organization",
    )


async def get_current_org(
    org_id: int = Depends(get_current_org_id),
) -> int:
    return org_id


# ── 权限校验 ──


def check_permission(perm_code: str):
    """RBAC 权限校验依赖"""

    async def permission_dependency(
        db: AsyncSession = Depends(get_db),
        org_user: OrganizationUser = Depends(get_current_org_user),
    ) -> OrganizationUser:
        if org_user.user_type != "staff":
            raise HTTPException(status_code=403, detail="Access denied. Staff only.")

        if not org_user.rbac_roles:
            raise HTTPException(status_code=403, detail="No roles assigned to user")

        role_ids = [r.id for r in org_user.rbac_roles]
        effective_permissions = await RBACService.get_effective_permissions(
            db, role_ids
        )

        if perm_code not in effective_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permission: {perm_code}",
            )
        return org_user

    return permission_dependency


# ── 配额校验 ──


async def verify_quota(
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> Tenant:
    """校验租户级配额"""
    from app.services.system.quota import check_tenant_quota

    return await check_tenant_quota(db, tenant_id)


# ── API Key 认证 ──


async def get_api_key_context(
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db),
) -> ApiKey:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization header")

    token = authorization.replace("Bearer ", "")
    token_hash = hmac.new(
        settings.API_KEY_SALT.encode(), token.encode(), hashlib.sha256
    ).hexdigest()

    stmt = select(ApiKey).where(
        ApiKey.key_hash == token_hash, ApiKey.status == "active"
    )
    result = await db.execute(stmt)
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(status_code=401, detail="Invalid API Key")

    if api_key.expires_at is not None:
        if api_key.expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=401, detail="API Key has expired")

    # Rate Limiting
    from app.services.system.quota import check_api_key_rate_limit

    await check_api_key_rate_limit(api_key.id, api_key.qps_limit)

    # Tenant quota
    from app.services.system.quota import check_tenant_quota

    await check_tenant_quota(db, api_key.tenant_id)

    # Key level quota
    if api_key.token_quota is not None and api_key.token_used >= api_key.token_quota:
        raise HTTPException(status_code=402, detail="API Key token quota exceeded")

    # RLS
    await db.execute(
        text("SELECT set_config('app.current_tenant_id', :tid, true)"),
        {"tid": str(api_key.tenant_id)},
    )

    return api_key


# ── 平台管理员 ──


async def get_platform_admin(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """验证用户拥有 platform_admin 角色"""
    from app.models import OrganizationUserRole

    stmt = (
        select(OrganizationUserRole)
        .join(Role, Role.id == OrganizationUserRole.role_id)
        .where(
            OrganizationUserRole.user_id == current_user.id,
            Role.code == "platform_admin",
            Role.tenant_id.is_(None),
        )
    )
    result = await db.execute(stmt)
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Platform admin access required")
    return current_user


async def get_platform_viewer(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """验证用户拥有 platform_admin 或 platform_viewer 角色"""
    from app.models import OrganizationUserRole

    stmt = (
        select(OrganizationUserRole)
        .join(Role, Role.id == OrganizationUserRole.role_id)
        .where(
            OrganizationUserRole.user_id == current_user.id,
            Role.code.in_(["platform_admin", "platform_viewer"]),
            Role.tenant_id.is_(None),
        )
    )
    result = await db.execute(stmt)
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Platform access required")
    return current_user


def check_org_admin():
    """检查用户是否是当前组织的管理员 (owner/admin)"""

    async def _check(
        db: AsyncSession = Depends(get_db),
        org_user: OrganizationUser = Depends(get_current_org_user),
    ) -> OrganizationUser:
        if org_user.user_type != "staff":
            raise HTTPException(status_code=403, detail="Access denied. Staff only.")
        if not org_user.rbac_roles:
            raise HTTPException(status_code=403, detail="No roles assigned to user")

        role_ids = [r.id for r in org_user.rbac_roles]
        all_role_ids = await RBACService.get_all_role_ids(db, role_ids)

        stmt = select(Role.code).where(Role.id.in_(list(all_role_ids)))
        result = await db.execute(stmt)
        all_role_codes = {row[0] for row in result.fetchall()}

        if not all_role_codes.intersection({"owner", "admin"}):
            raise HTTPException(
                status_code=403, detail="Organization admin access required"
            )
        return org_user

    return _check


# ── Service 依赖注入工厂 ──

S = TypeVar("S")


def ServiceDep(service_cls: type[S]):
    """通用 Service 依赖工厂

    用法：
        PatientServiceDep = Annotated[PatientService, ServiceDep(PatientService)]
    """

    async def _factory(db: AsyncSession = Depends(get_db)) -> S:
        return service_cls(db)

    return Depends(_factory)


# ── Patient 领域 ──
from app.services.patient.patient_service import PatientService

PatientServiceDep = Annotated[PatientService, ServiceDep(PatientService)]

from app.services.patient.health_metric_service import HealthMetricService

HealthMetricServiceDep = Annotated[HealthMetricService, ServiceDep(HealthMetricService)]

from app.services.patient.manager_service import ManagerService

ManagerServiceDep = Annotated[ManagerService, ServiceDep(ManagerService)]

from app.services.patient.family_service import FamilyService

FamilyServiceDep = Annotated[FamilyService, ServiceDep(FamilyService)]

# ── System 领域 ──
from app.services.system.org_service import OrgService

OrgServiceDep = Annotated[OrgService, ServiceDep(OrgService)]

from app.services.system.user_service import UserService

UserServiceDep = Annotated[UserService, ServiceDep(UserService)]

from app.services.system.tenant_service import TenantService

TenantServiceDep = Annotated[TenantService, ServiceDep(TenantService)]

from app.services.system.dashboard_service import DashboardService

DashboardServiceDep = Annotated[DashboardService, ServiceDep(DashboardService)]

from app.services.system.menu_service import MenuService

MenuServiceDep = Annotated[MenuService, ServiceDep(MenuService)]

from app.services.system.rbac_service import RBACServiceExt

RBACServiceDep = Annotated[RBACServiceExt, ServiceDep(RBACServiceExt)]

# ── RAG 领域 ──
from app.services.rag.kb_service import KBService

KBServiceDep = Annotated[KBService, ServiceDep(KBService)]

from app.services.rag.conversation_service import ConversationService

ConversationServiceDep = Annotated[ConversationService, ServiceDep(ConversationService)]

# ── Auth 领域 ──
from app.services.auth.auth_service import AuthService

AuthServiceDep = Annotated[AuthService, ServiceDep(AuthService)]

# ── 独立适配器 ──
from app.services.system.settings_adapter import SettingsServiceAdapter

SettingsServiceDep = Annotated[SettingsServiceAdapter, ServiceDep(SettingsServiceAdapter)]
