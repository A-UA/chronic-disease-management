from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List

from app.api.deps import get_db, get_platform_admin, get_platform_viewer
from app.db.models import User, OrganizationUser
from app.schemas.admin import UserAdminRead

router = APIRouter()


from app.core import security
from app.schemas.user import UserCreate

@router.post("", response_model=UserAdminRead)
async def create_user(
    user_in: UserCreate,
    _admin=Depends(get_platform_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    [平台管理员] 手动创建一个新用户
    """
    # Check if exists
    stmt = select(User).where(User.email == user_in.email)
    res = await db.execute(stmt)
    if res.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User already exists")
    
    user = User(
        email=user_in.email,
        password_hash=security.get_password_hash(user_in.password),
        name=user_in.name
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return UserAdminRead(
        id=user.id,
        email=user.email,
        name=user.name,
        created_at=user.created_at,
        org_count=0
    )


@router.get("", response_model=List[UserAdminRead])
async def list_users(
    skip: int = 0,
    limit: int = 50,
    search: str | None = None,
    _admin=Depends(get_platform_viewer),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(User)
    if search:
        stmt = stmt.where(
            User.email.ilike(f"%{search}%") | User.name.ilike(f"%{search}%")
        )
    stmt = stmt.offset(skip).limit(limit).order_by(User.created_at.desc())
    result = await db.execute(stmt)
    users = result.scalars().all()

    user_reads = []
    for user in users:
        count_stmt = select(func.count()).where(OrganizationUser.user_id == user.id)
        count = (await db.execute(count_stmt)).scalar() or 0
        user_reads.append(
            UserAdminRead(
                id=user.id,
                email=user.email,
                name=user.name,
                created_at=user.created_at,
                org_count=count,
            )
        )
    return user_reads


@router.get("/{user_id}", response_model=UserAdminRead)
async def get_user(
    user_id: int,
    _admin=Depends(get_platform_viewer),
    db: AsyncSession = Depends(get_db),
):
    """[平台管理员] 获取用户详情"""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    count_stmt = select(func.count()).where(OrganizationUser.user_id == user.id)
    count = (await db.execute(count_stmt)).scalar() or 0
    return UserAdminRead(
        id=user.id, email=user.email, name=user.name,
        created_at=user.created_at, org_count=count,
    )


from pydantic import BaseModel as _BaseModel
from typing import Optional


class UserUpdate(_BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None


@router.put("/{user_id}", response_model=UserAdminRead)
async def update_user(
    user_id: int,
    data: UserUpdate,
    _admin=Depends(get_platform_admin),
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
        id=user.id, email=user.email, name=user.name,
        created_at=user.created_at, org_count=count,
    )


@router.put("/{user_id}/status")
async def update_user_status(
    user_id: int,
    is_active: bool,
    _admin=Depends(get_platform_admin),
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
    _admin=Depends(get_platform_admin),
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
