import json
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
from app.services.rbac import RBACService
from app.services.quota import check_org_quota, check_api_key_rate_limit, get_redis_client
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


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    return current_user


async def get_current_org_user(
    x_organization_id: str | None = Header(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrganizationUser:
    """
    获取当前用户在当前组织上下文中的身份。
    支持租户超管穿透：如果用户是根组织的管理员，可以访问其所有子组织。
    """
    requested_org_id: int | None = None
    if x_organization_id:
        try:
            requested_org_id = int(x_organization_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid Organization ID")

    # 1. 尝试直接获取该用户在该组织的显式身份
    stmt = (
        select(OrganizationUser)
        .options(
            selectinload(OrganizationUser.rbac_roles).selectinload(Role.permissions)
        )
        .where(
            OrganizationUser.user_id == current_user.id,
        )
    )
    if requested_org_id:
        stmt = stmt.where(OrganizationUser.org_id == requested_org_id)
    else:
        # 如果没传，默认取第一个组织
        stmt = stmt.limit(1)
    
    result = await db.execute(stmt)
    org_user = result.scalar_one_or_none()

    # 2. 如果没有显式身份，且传了 org_id，检查是否是租户超管穿透
    if not org_user and requested_org_id:
        # 查找用户所属的所有根组织且拥有 admin/owner 权限
        all_stmt = select(OrganizationUser).options(
            selectinload(OrganizationUser.rbac_roles)
        ).where(OrganizationUser.user_id == current_user.id)
        all_result = await db.execute(all_stmt)
        user_orgs = all_result.scalars().all()

        root_org_admin_ids = []
        for ou in user_orgs:
            if any(r.code in ["owner", "admin"] for r in ou.rbac_roles):
                root_org_admin_ids.append(ou.org_id)
        
        if root_org_admin_ids:
            # 检查请求的 org_id 是否在这些管理组织的子树中
            # 引入 Redis 缓存以提高性能
            redis = get_redis_client()
            is_valid_child = False
            root_id_of_access = None

            for root_id in root_org_admin_ids:
                cache_key = f"org:tree:{root_id}"
                try:
                    cached_data = await redis.get(cache_key)
                    if cached_data:
                        tree_ids = set(json.loads(cached_data))
                    else:
                        # 缓存缺失，执行递归查询并填充
                        tree_stmt = text("""
                            WITH RECURSIVE org_tree AS (
                                SELECT id FROM organizations WHERE id = :root_id
                                UNION ALL
                                SELECT o.id FROM organizations o INNER JOIN org_tree ot ON o.parent_id = ot.id
                            )
                            SELECT id FROM org_tree
                        """)
                        tree_res = await db.execute(tree_stmt, {"root_id": root_id})
                        tree_ids = {row[0] for row in tree_res.fetchall()}
                        await redis.set(cache_key, json.dumps(list(tree_ids)), ex=3600)
                    
                    if requested_org_id in tree_ids:
                        is_valid_child = True
                        root_id_of_access = root_id
                        break
                except Exception as e:
                    logger.warning(f"Redis cache access failed in get_current_org_user: {e}")
                    # 回退到直接数据库检查
                    check_stmt = text("""
                        WITH RECURSIVE org_tree AS (
                            SELECT id FROM organizations WHERE id = :root_id
                            UNION ALL
                            SELECT o.id FROM organizations o INNER JOIN org_tree ot ON o.parent_id = ot.id
                        )
                        SELECT 1 FROM org_tree WHERE id = :target_id LIMIT 1
                    """)
                    if (await db.execute(check_stmt, {"root_id": root_id, "target_id": requested_org_id})).scalar():
                        is_valid_child = True
                        root_id_of_access = root_id
                        break
            
            if is_valid_child:
                # 是子组织！找到用户在哪个根组织下拥有的权限
                root_ou = next(ou for ou in user_orgs if ou.org_id == root_id_of_access)
                
                # 构造一个临时的 OrganizationUser 对象
                roles_copy = [role for role in root_ou.rbac_roles]
                
                org_user = OrganizationUser(
                    org_id=requested_org_id,
                    user_id=current_user.id,
                    user_type=root_ou.user_type,
                    rbac_roles=roles_copy
                )

    if not org_user:
        raise HTTPException(
            status_code=403, detail="Not enough permissions or no organization context"
        )

    # 3. 注入 RLS 上下文
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
        db: AsyncSession = Depends(get_db),
        org_user: OrganizationUser = Depends(get_current_org_user),
    ) -> OrganizationUser:
        # 1. Functional RBAC is only for staff
        if org_user.user_type != "staff":
            raise HTTPException(status_code=403, detail="Access denied. Staff only.")

        # 2. Advanced RBAC check (Hierarchical)
        if not org_user.rbac_roles:
            raise HTTPException(status_code=403, detail="No roles assigned to user")

        role_ids = [r.id for r in org_user.rbac_roles]
        effective_permissions = await RBACService.get_effective_permissions(db, role_ids)

        if perm_code not in effective_permissions:
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
        db: AsyncSession = Depends(get_db),
        org_user: OrganizationUser = Depends(get_current_org_user),
    ) -> OrganizationUser:
        if org_user.user_type != "staff":
            raise HTTPException(status_code=403, detail="Access denied. Staff only.")
        if not org_user.rbac_roles:
            raise HTTPException(status_code=403, detail="No roles assigned to user")

        # Resolve all inherited roles
        role_ids = [r.id for r in org_user.rbac_roles]
        all_role_ids = await RBACService.get_all_role_ids(db, role_ids)

        # Get all role codes (direct + inherited)
        stmt = select(Role.code).where(Role.id.in_(list(all_role_ids)))
        result = await db.execute(stmt)
        all_role_codes = {row[0] for row in result.fetchall()}

        if not all_role_codes.intersection({"owner", "admin"}):
            raise HTTPException(
                status_code=403, detail="Organization admin access required"
            )
        return org_user

    return _check
