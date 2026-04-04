"""依赖注入：认证 → 租户上下文 → 部门上下文 → 权限校验"""

import json
import logging
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Header, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import jwt
import hashlib
import hmac

from app.core.config import settings
from app.core.security import ALGORITHM
from app.db.session import get_db
from app.db.models import (
    User, Organization, OrganizationUser, ApiKey, Role, Permission, Tenant,
)
from app.services.rbac import RBACService

logger = logging.getLogger(__name__)

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
                detail="Token does not contain tenant context. Please select a tenant.",
            )
        return int(tenant_id)
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


# ── 第 3 层：RLS 上下文注入 ──

async def inject_rls_context(
    tenant_id: int = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> int:
    """将 tenant_id 和 user_id 注入 PostgreSQL 会话变量，用于 RLS"""
    await db.execute(
        text("SELECT set_config('app.current_tenant_id', :tid, true)"),
        {"tid": str(tenant_id)},
    )
    # user_id 已在 get_current_user 中注入
    return tenant_id


# ── 第 4 层：部门上下文（从 Header 读取，可选） ──

async def get_current_org_user(
    request: Request,
    tenant_id: int = Depends(inject_rls_context),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrganizationUser:
    """从 X-Organization-ID 请求头获取部门上下文，支持管理员穿透"""
    org_id_header = request.headers.get("X-Organization-ID")
    requested_org_id: int | None = None

    if org_id_header:
        try:
            requested_org_id = int(org_id_header)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid Organization ID")

    if requested_org_id is None:
        # 未指定部门 → 取用户在该租户下的第一个部门
        stmt = (
            select(OrganizationUser)
            .where(
                OrganizationUser.tenant_id == tenant_id,
                OrganizationUser.user_id == current_user.id,
            )
            .options(
                selectinload(OrganizationUser.rbac_roles).selectinload(Role.permissions)
            )
            .limit(1)
        )
        result = await db.execute(stmt)
        org_user = result.scalar_one_or_none()
        if not org_user:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is not a member of any organization in this tenant",
            )
        return org_user

    # 有指定部门 → 校验归属
    org = await db.get(Organization, requested_org_id)
    if not org or org.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization does not belong to current tenant",
        )

    # 尝试直接获取用户在该部门的身份
    stmt = (
        select(OrganizationUser)
        .where(
            OrganizationUser.org_id == requested_org_id,
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

    # 不是直接成员 → 检查是否是租户管理员（穿透访问）
    stmt_admin = (
        select(OrganizationUser)
        .where(
            OrganizationUser.tenant_id == tenant_id,
            OrganizationUser.user_id == current_user.id,
        )
        .options(selectinload(OrganizationUser.rbac_roles))
    )
    result_admin = await db.execute(stmt_admin)
    admin_org_users = result_admin.scalars().all()

    for ou in admin_org_users:
        role_codes = {r.code for r in ou.rbac_roles}
        if role_codes & {"admin", "owner"}:
            # 构造临时 OrganizationUser 实现穿透
            return OrganizationUser(
                tenant_id=tenant_id,
                org_id=requested_org_id,
                user_id=current_user.id,
                user_type=ou.user_type,
                rbac_roles=list(ou.rbac_roles),
            )

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Not a member of this organization",
    )


async def get_current_org(
    org_user: OrganizationUser = Depends(get_current_org_user),
) -> int:
    return org_user.org_id


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
    from app.services.quota import check_tenant_quota
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
    from app.services.quota import check_api_key_rate_limit
    await check_api_key_rate_limit(api_key.id, api_key.qps_limit)

    # Tenant quota
    from app.services.quota import check_tenant_quota
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
    from app.db.models import OrganizationUserRole

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
    from app.db.models import OrganizationUserRole

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
