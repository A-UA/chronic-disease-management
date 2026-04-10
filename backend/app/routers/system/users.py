from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import OrganizationUser, User
from app.routers.deps import (
    check_permission,
    get_current_org_id,
    get_current_tenant_id,
    get_db,
)
from app.schemas.admin import UserAdminRead

router = APIRouter()


from pydantic import BaseModel as _PydanticBase

from app.base import security


class UserCreateAdmin(_PydanticBase):
    email: str
    password: str
    name: str | None = None
    org_id: int | None = None  # 要绑定的组织 ID（可选，默认绑定当前组织）
    role_ids: list[int] | None = None  # 要分配的角色 ID 列表


@router.post("", response_model=UserAdminRead)
async def create_user(
    user_in: UserCreateAdmin,
    tenant_id: int = Depends(get_current_tenant_id),
    current_org_id: int = Depends(get_current_org_id),
    _admin=Depends(check_permission("org_member:manage")),
    db: AsyncSession = Depends(get_db),
):
    """
    [平台管理员] 创建用户并绑定到组织+角色
    """
    # Check if exists
    stmt = select(User).where(User.email == user_in.email)
    res = await db.execute(stmt)
    if res.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User already exists")

    user = User(
        email=user_in.email,
        password_hash=security.get_password_hash(user_in.password),
        name=user_in.name,
    )
    db.add(user)
    await db.flush()

    # 绑定到组织（优先使用传入的 org_id，否则绑定到当前操作者的组织）
    target_org_id = user_in.org_id or current_org_id
    from app.models import OrganizationUserRole, Role

    org_user = OrganizationUser(
        tenant_id=tenant_id,
        org_id=target_org_id,
        user_id=user.id,
        user_type="staff",
    )
    db.add(org_user)
    await db.flush()

    # 分配角色（如果传入了 role_ids）
    if user_in.role_ids:
        for rid in user_in.role_ids:
            db.add(
                OrganizationUserRole(
                    tenant_id=tenant_id,
                    org_id=target_org_id,
                    user_id=user.id,
                    role_id=rid,
                )
            )
    else:
        # 默认分配 staff 角色
        stmt_role = select(Role).where(
            Role.code == "staff",
            (Role.tenant_id == tenant_id) | (Role.tenant_id.is_(None)),
        )
        staff_role = (await db.execute(stmt_role)).scalars().first()
        if staff_role:
            db.add(
                OrganizationUserRole(
                    tenant_id=tenant_id,
                    org_id=target_org_id,
                    user_id=user.id,
                    role_id=staff_role.id,
                )
            )

    await db.commit()
    await db.refresh(user)

    return UserAdminRead(
        id=user.id,
        email=user.email,
        name=user.name,
        created_at=user.created_at,
        org_count=1,
    )


@router.get("")
async def list_users(
    skip: int = 0,
    limit: int = 50,
    search: str | None = None,
    tenant_id: int = Depends(get_current_tenant_id),
    _admin=Depends(check_permission("org_member:manage")),
    db: AsyncSession = Depends(get_db),
):
    """[管理员] 列出当前租户下的所有用户"""
    # 通过 organization_users 关联找出属于当前租户的用户
    base = (
        select(User)
        .join(OrganizationUser, OrganizationUser.user_id == User.id)
        .where(OrganizationUser.tenant_id == tenant_id)
        .distinct()
    )
    if search:
        base = base.where(
            User.email.ilike(f"%{search}%") | User.name.ilike(f"%{search}%")
        )

    count_stmt = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    stmt = base.order_by(User.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    users = result.scalars().all()

    user_reads = []
    for user in users:
        count_org = select(func.count()).where(OrganizationUser.user_id == user.id)
        count = (await db.execute(count_org)).scalar() or 0
        user_reads.append(
            UserAdminRead(
                id=user.id,
                email=user.email,
                name=user.name,
                created_at=user.created_at,
                org_count=count,
            )
        )
    return {"total": total, "items": user_reads}


@router.get("/{user_id}", response_model=UserAdminRead)
async def get_user(
    user_id: int,
    _admin=Depends(check_permission("org_member:manage")),
    db: AsyncSession = Depends(get_db),
):
    """[平台管理员] 获取用户详情"""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    count_stmt = select(func.count()).where(OrganizationUser.user_id == user.id)
    count = (await db.execute(count_stmt)).scalar() or 0
    return UserAdminRead(
        id=user.id,
        email=user.email,
        name=user.name,
        created_at=user.created_at,
        org_count=count,
    )


from pydantic import BaseModel as _BaseModel


class UserUpdate(_BaseModel):
    name: str | None = None
    email: str | None = None


@router.put("/{user_id}", response_model=UserAdminRead)
async def update_user(
    user_id: int,
    data: UserUpdate,
    _admin=Depends(check_permission("org_member:manage")),
    db: AsyncSession = Depends(get_db),
):
    """[平台管理员] 编辑用户信息"""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if data.email and data.email != user.email:
        dup = select(User).where(User.email == data.email, User.id != user_id)
        if (await db.execute(dup)).scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already in use")
        user.email = data.email
    if data.name is not None:
        user.name = data.name

    await db.commit()
    await db.refresh(user)
    count_stmt = select(func.count()).where(OrganizationUser.user_id == user.id)
    count = (await db.execute(count_stmt)).scalar() or 0
    return UserAdminRead(
        id=user.id,
        email=user.email,
        name=user.name,
        created_at=user.created_at,
        org_count=count,
    )


@router.put("/{user_id}/status")
async def update_user_status(
    user_id: int,
    is_active: bool,
    _admin=Depends(check_permission("org_member:manage")),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if is_active:
        user.deleted_at = None
    else:
        from sqlalchemy.sql import func as sqlfunc

        user.deleted_at = sqlfunc.now()
    await db.commit()
    return {"status": "ok"}


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    _admin=Depends(check_permission("org_member:manage")),
    db: AsyncSession = Depends(get_db),
):
    """[平台管理员] 删除用户（软删除）"""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    from sqlalchemy.sql import func as sqlfunc

    user.deleted_at = sqlfunc.now()
    await db.commit()
    return {"status": "ok"}
