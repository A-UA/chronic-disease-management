from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
import jwt
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from app.core.config import settings
from app.core.security import ALGORITHM
from app.db.session import get_db
from sqlalchemy.orm import selectinload
from app.db.models import User, OrganizationUser, Organization, ApiKey, Role, Permission
from app.services.quota import check_org_quota, check_api_key_rate_limit
import hashlib
import hmac

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login/access-token"
)


async def get_current_user(
    db: AsyncSession = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> User:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except (jwt.PyJWTError, ValidationError):
        raise HTTPException(status_code=401, detail="Could not validate credentials")

    user = await db.get(User, int(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Inject User ID for RLS (e.g. for cross-org family access)
    await db.execute(
        text("SELECT set_config('app.current_user_id', :user_id, true)"),
        {"user_id": str(user.id)},
    )

    return user


async def get_current_org_user(
    x_organization_id: str | None = Header(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrganizationUser:
    org_uuid: int | None = None
    if x_organization_id:
        try:
            org_uuid = int(x_organization_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid Organization ID")

    if org_uuid:
        # Verify user belongs to org and load RBAC info
        stmt = (
            select(OrganizationUser)
            .options(
                selectinload(OrganizationUser.rbac_roles).selectinload(Role.permissions)
            )
            .where(
                OrganizationUser.org_id == org_uuid,
                OrganizationUser.user_id == current_user.id,
            )
        )
        result = await db.execute(stmt)
        org_user = result.scalar_one_or_none()
    else:
        # Fallback to the first organization the user belongs to
        stmt = (
            select(OrganizationUser)
            .options(
                selectinload(OrganizationUser.rbac_roles).selectinload(Role.permissions)
            )
            .where(OrganizationUser.user_id == current_user.id)
            .limit(1)
        )
        result = await db.execute(stmt)
        org_user = result.scalar_one_or_none()

    if not org_user:
        raise HTTPException(
            status_code=403, detail="Not enough permissions or no organization context"
        )

    # Inject RLS context
    await db.execute(
        text("SELECT set_config('app.current_org_id', :org_id, true)"),
        {"org_id": str(org_user.org_id)},
    )

    return org_user


async def get_current_org(
    org_user: OrganizationUser = Depends(get_current_org_user),
) -> int:
    return org_user.org_id


def check_permission(perm_code: str):
    async def permission_dependency(
        org_user: OrganizationUser = Depends(get_current_org_user),
    ) -> OrganizationUser:
        # 1. Functional RBAC is only for staff
        if org_user.user_type != "staff":
            raise HTTPException(status_code=403, detail="Access denied. Staff only.")

        # 2. Standard RBAC check
        if not org_user.rbac_roles:
            raise HTTPException(status_code=403, detail="No roles assigned to user")

        permissions = {p.code for role in org_user.rbac_roles for p in role.permissions}
        if perm_code not in permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permission: {perm_code}",
            )
        return org_user

    return permission_dependency


async def verify_quota(
    org_id: int = Depends(get_current_org), db: AsyncSession = Depends(get_db)
) -> Organization:
    return await check_org_quota(db, org_id)


async def get_api_key_context(
    authorization: str = Header(...), db: AsyncSession = Depends(get_db)
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

    # Rate Limiting
    await check_api_key_rate_limit(api_key.id, api_key.qps_limit)

    # Verify Quota (org level)
    await check_org_quota(db, api_key.org_id)

    # Key level quota if exists
    if api_key.token_quota is not None and api_key.token_used >= api_key.token_quota:
        raise HTTPException(status_code=402, detail="API Key token quota exceeded")

    # RLS
    await db.execute(
        text("SELECT set_config('app.current_org_id', :org_id, true)"),
        {"org_id": str(api_key.org_id)},
    )

    return api_key


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
            Role.org_id.is_(None),
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
            Role.org_id.is_(None),
        )
    )
    result = await db.execute(stmt)
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Platform access required")
    return current_user


def check_org_admin():
    """检查用户是否是当前组织的管理员 (owner/admin)"""

    async def _check(
        org_user: OrganizationUser = Depends(get_current_org_user),
    ) -> OrganizationUser:
        if org_user.user_type != "staff":
            raise HTTPException(status_code=403, detail="Access denied. Staff only.")
        if not org_user.rbac_roles:
            raise HTTPException(status_code=403, detail="No roles assigned to user")
        role_codes = {r.code for r in org_user.rbac_roles}
        if not role_codes.intersection({"owner", "admin"}):
            raise HTTPException(
                status_code=403, detail="Organization admin access required"
            )
        return org_user

    return _check
