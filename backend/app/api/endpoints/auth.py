from datetime import timedelta, datetime, timezone
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.api.deps import (
    get_db, get_current_user, get_current_org_user,
    get_current_tenant_id, inject_rls_context,
)
from app.core import security
from app.core.config import settings
from app.db.models import (
    User,
    Tenant,
    Organization,
    OrganizationUser,
    OrganizationUserRole,
    Role,
    Permission,
)
from app.services.rbac import RBACService
from app.schemas.user import UserCreate, Token, UserRead, UserUpdatePassword

from app.db.models.menu import Menu
from pydantic import BaseModel, EmailStr
import jwt as pyjwt

router = APIRouter()


@router.post("/register", response_model=Any)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)) -> Any:
    # 1. 检查用户是否存在
    stmt = select(User).where(User.email == user_in.email)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=400, detail="The user with this email already exists."
        )

    # 2. 创建用户
    user = User(
        email=user_in.email,
        password_hash=security.get_password_hash(user_in.password),
        name=user_in.name,
    )
    db.add(user)
    await db.flush()

    # 3. 创建默认租户
    tenant = Tenant(
        name=f"{user.name or user.email}'s Workspace",
        slug=f"ws-{user.id}",
        plan_type="free",
    )
    db.add(tenant)
    await db.flush()

    # 4. 创建默认部门
    org = Organization(tenant_id=tenant.id, name="默认部门", code="DEFAULT")
    db.add(org)
    await db.flush()

    # 5. 绑定用户到部门
    org_user = OrganizationUser(
        tenant_id=tenant.id, org_id=org.id, user_id=user.id,
    )
    db.add(org_user)

    # 6. 分配 owner 角色
    stmt_role = select(Role).where(Role.code == "owner", Role.tenant_id.is_(None))
    res = await db.execute(stmt_role)
    owner_role = res.scalar_one_or_none()
    if owner_role:
        role_link = OrganizationUserRole(
            tenant_id=tenant.id, org_id=org.id,
            user_id=user.id, role_id=owner_role.id,
        )
        db.add(role_link)

    # 7. 如果是系统第一个用户，分配 platform_admin 角色
    stmt_user_count = select(func.count(User.id))
    user_count_res = await db.execute(stmt_user_count)
    if user_count_res.scalar() == 1:
        stmt_platform_role = select(Role).where(
            Role.code == "platform_admin", Role.tenant_id.is_(None)
        )
        res_platform = await db.execute(stmt_platform_role)
        platform_role = res_platform.scalar_one_or_none()
        if platform_role:
            role_link_platform = OrganizationUserRole(
                tenant_id=tenant.id, org_id=org.id,
                user_id=user.id, role_id=platform_role.id,
            )
            db.add(role_link_platform)

    await db.commit()
    await db.refresh(user)

    return {
        "id": user.id, "email": user.email,
        "tenant_id": tenant.id, "org_id": org.id,
    }


@router.post("/login/access-token")
async def login_access_token(
    db: AsyncSession = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Any:
    # 1. 认证
    stmt = select(User).where(User.email == form_data.username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not security.verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect email or password")

    # 2. 查用户所属租户列表
    stmt_tenants = (
        select(Tenant)
        .join(Organization, Organization.tenant_id == Tenant.id)
        .join(OrganizationUser, OrganizationUser.org_id == Organization.id)
        .where(OrganizationUser.user_id == user.id, Tenant.status == "active")
        .distinct()
    )
    result_tenants = await db.execute(stmt_tenants)
    tenants = result_tenants.scalars().all()

    if len(tenants) == 0:
        raise HTTPException(
            status_code=400,
            detail="User is not a member of any active tenant",
        )

    if len(tenants) == 1:
        # 单租户 → 自动签发含 tenant_id 的 JWT
        tenant = tenants[0]
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        token = security.create_access_token(
            user.id, tenant_id=tenant.id, expires_delta=access_token_expires,
        )
        return {
            "access_token": token,
            "token_type": "bearer",
            "tenant": {"id": tenant.id, "name": tenant.name},
            "require_tenant_selection": False,
        }

    # 多租户 → 返回选择列表 + 临时 token
    selection_token = security.create_selection_token(user.id)
    return {
        "access_token": None,
        "token_type": "bearer",
        "tenants": [{"id": t.id, "name": t.name} for t in tenants],
        "require_tenant_selection": True,
        "selection_token": selection_token,
    }


class SelectTenantRequest(BaseModel):
    tenant_id: int
    selection_token: str


@router.post("/select-tenant")
async def select_tenant(
    data: SelectTenantRequest,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """多租户用户登录后选择租户"""
    try:
        payload = pyjwt.decode(
            data.selection_token, settings.JWT_SECRET, algorithms=[security.ALGORITHM]
        )
        if payload.get("purpose") != "tenant_selection":
            raise HTTPException(status_code=400, detail="Invalid selection token")
        user_id = int(payload["sub"])
    except pyjwt.PyJWTError:
        raise HTTPException(
            status_code=400, detail="Invalid or expired selection token"
        )

    # 校验用户确实属于该租户
    stmt = (
        select(OrganizationUser)
        .join(Organization, Organization.id == OrganizationUser.org_id)
        .where(
            OrganizationUser.user_id == user_id,
            Organization.tenant_id == data.tenant_id,
        )
        .limit(1)
    )
    result = await db.execute(stmt)
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=403, detail="User is not a member of this tenant"
        )

    tenant = await db.get(Tenant, data.tenant_id)
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = security.create_access_token(
        user_id, tenant_id=tenant.id, expires_delta=access_token_expires,
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "tenant": {"id": tenant.id, "name": tenant.name},
    }


class SwitchTenantRequest(BaseModel):
    tenant_id: int


@router.post("/switch-tenant")
async def switch_tenant(
    data: SwitchTenantRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """已登录用户切换租户"""
    stmt = (
        select(OrganizationUser)
        .join(Organization, Organization.id == OrganizationUser.org_id)
        .where(
            OrganizationUser.user_id == current_user.id,
            Organization.tenant_id == data.tenant_id,
        )
        .limit(1)
    )
    result = await db.execute(stmt)
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=403, detail="User is not a member of this tenant"
        )

    tenant = await db.get(Tenant, data.tenant_id)
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = security.create_access_token(
        current_user.id, tenant_id=tenant.id, expires_delta=access_token_expires,
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "tenant": {"id": tenant.id, "name": tenant.name},
    }


@router.get("/tenants")
async def list_my_tenants(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """获取当前用户可用的租户列表"""
    stmt = (
        select(Tenant)
        .join(Organization, Organization.tenant_id == Tenant.id)
        .join(OrganizationUser, OrganizationUser.org_id == Organization.id)
        .where(OrganizationUser.user_id == current_user.id, Tenant.status == "active")
        .distinct()
    )
    result = await db.execute(stmt)
    tenants = result.scalars().all()
    return [
        {"id": t.id, "name": t.name, "plan_type": t.plan_type, "status": t.status}
        for t in tenants
    ]


@router.get("/me", response_model=UserRead)
async def read_current_user(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """获取当前登录用户信息（包含组织 ID 和递归有效权限）"""
    stmt = (
        select(User)
        .options(
            selectinload(User.organizations).selectinload(OrganizationUser.rbac_roles)
        )
        .where(User.id == current_user.id)
    )
    res = await db.execute(stmt)
    full_user = res.scalar_one()

    user_data = UserRead.model_validate(full_user)
    if full_user.organizations:
        org_user = full_user.organizations[0]
        user_data.org_id = org_user.org_id
        user_data.tenant_id = org_user.tenant_id

        if org_user.rbac_roles:
            role_ids = [r.id for r in org_user.rbac_roles]
            user_data.permissions = list(
                await RBACService.get_effective_permissions(db, role_ids)
            )
        else:
            user_data.permissions = []
    else:
        user_data.permissions = []

    return user_data


@router.get("/menu-tree")
async def get_menu_tree(
    db: AsyncSession = Depends(get_db),
    org_user: OrganizationUser = Depends(get_current_org_user),
    tenant_id: int = Depends(get_current_tenant_id),
) -> Any:
    """获取当前用户的动态导航菜单（从 menus 表读取，树形嵌套返回）"""
    # 1. 计算用户的所有有效权限编码
    role_ids = [r.id for r in org_user.rbac_roles]
    all_role_ids = await RBACService.get_all_role_ids(db, role_ids)

    stmt = (
        select(Permission.code)
        .join(Permission.roles)
        .where(Role.id.in_(list(all_role_ids)))
        .distinct()
    )
    result = await db.execute(stmt)
    user_permission_codes = {row[0] for row in result.all()}

    # 2. 查询所有系统级菜单（tenant_id IS NULL）+ 本租户定制菜单
    stmt = (
        select(Menu)
        .where(
            Menu.is_enabled == True,
            Menu.deleted_at.is_(None),
            (Menu.tenant_id.is_(None)) | (Menu.tenant_id == tenant_id),
        )
        .order_by(Menu.sort)
    )
    result = await db.execute(stmt)
    all_menus = result.scalars().all()

    # 3. 过滤权限
    visible_menus = []
    for menu in all_menus:
        if not menu.permission_code or menu.permission_code in user_permission_codes:
            visible_menus.append(menu)

    # 4. 组装树形结构
    menu_map = {}
    for m in visible_menus:
        menu_map[m.id] = {
            "id": m.id,
            "name": m.name,
            "code": m.code,
            "menu_type": m.menu_type,
            "path": m.path,
            "icon": m.icon,
            "permission_code": m.permission_code,
            "sort": m.sort,
            "is_visible": m.is_visible,
            "is_enabled": m.is_enabled,
            "meta": m.meta,
            "children": [],
        }
    roots = []
    visible_ids = {m.id for m in visible_menus}

    for m in visible_menus:
        node = menu_map[m.id]
        if m.parent_id and m.parent_id in visible_ids:
            menu_map[m.parent_id]["children"].append(node)
        else:
            roots.append(node)

    # 5. 移除没有子节点的 directory 类型菜单
    def prune(items):
        return [
            item
            for item in items
            if item["menu_type"] != "directory" or len(item.get("children", [])) > 0
        ]

    return prune(roots)


@router.put("/update-password", response_model=dict)
async def update_password(
    data: UserUpdatePassword,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """修改当前用户的密码"""
    if not security.verify_password(data.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect current password")

    current_user.password_hash = security.get_password_hash(data.new_password)
    await db.commit()
    return {"message": "Password updated successfully"}


# ── 用户信息编辑 ──

class UserProfileUpdate(BaseModel):
    name: str | None = None


@router.put("/me/profile")
async def update_my_profile(
    data: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """修改当前用户基本信息（姓名等）"""
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)
    await db.commit()
    return {"status": "ok", "name": current_user.name}


# ── 密码重置 ──

class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    code: str
    new_password: str


@router.post("/forgot-password")
async def forgot_password(
    data: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """请求密码重置（无论邮箱是否存在都返回200，防信息泄露）"""
    import secrets
    import logging

    logger = logging.getLogger(__name__)

    stmt = select(User).where(User.email == data.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user:
        code = f"{secrets.randbelow(1000000):06d}"
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)

        from app.db.models import PasswordResetToken

        token = PasswordResetToken(
            user_id=user.id,
            token=code,
            expires_at=expires_at,
        )
        db.add(token)
        await db.commit()

        logger.info(
            f"[密码重置] 用户 {data.email} 的验证码: {code}（15分钟内有效）"
        )

    return {"message": "If the email exists, a reset code has been sent."}


@router.post("/reset-password")
async def reset_password(
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """使用验证码重置密码"""
    from app.db.models import PasswordResetToken

    stmt = (
        select(PasswordResetToken)
        .join(User, User.id == PasswordResetToken.user_id)
        .where(
            User.email == data.email,
            PasswordResetToken.token == data.code,
            PasswordResetToken.used == False,
        )
        .order_by(PasswordResetToken.created_at.desc())
    )
    result = await db.execute(stmt)
    reset_token = result.scalar_one_or_none()

    if not reset_token:
        raise HTTPException(status_code=400, detail="Invalid or expired reset code")

    now = datetime.now(timezone.utc)
    if reset_token.expires_at.tzinfo is None:
        expires = reset_token.expires_at.replace(tzinfo=timezone.utc)
    else:
        expires = reset_token.expires_at

    if expires < now:
        raise HTTPException(status_code=400, detail="Reset code has expired")

    user = await db.get(User, reset_token.user_id)
    user.password_hash = security.get_password_hash(data.new_password)
    reset_token.used = True
    await db.commit()
    return {"message": "Password has been reset successfully"}
