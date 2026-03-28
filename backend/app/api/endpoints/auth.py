from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.api.deps import get_db, get_current_user
from app.core import security
from app.core.config import settings
from app.db.models import (
    User,
    Organization,
    OrganizationUser,
    OrganizationUserRole,
    Role,
)
from app.schemas.user import UserCreate, Token, UserRead
from pydantic import BaseModel, EmailStr

router = APIRouter()


@router.post("/register", response_model=Any)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)) -> Any:
    # 1. Check if user exists
    stmt = select(User).where(User.email == user_in.email)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=400, detail="The user with this email already exists."
        )

    # 2. Create User
    user = User(
        email=user_in.email,
        password_hash=security.get_password_hash(user_in.password),
        name=user_in.name,
    )
    db.add(user)
    await db.flush()  # Get user.id

    # 3. Create Default Organization for User
    org = Organization(name=f"{user.name or user.email}'s Org", plan_type="free")
    db.add(org)
    await db.flush()  # Get org.id

    # 4. Bind User to Org
    org_user = OrganizationUser(org_id=org.id, user_id=user.id)
    db.add(org_user)

    # 5. Assign owner role
    stmt_role = select(Role).where(Role.code == "owner", Role.org_id.is_(None))
    res = await db.execute(stmt_role)
    owner_role = res.scalar_one_or_none()
    if owner_role:
        role_link = OrganizationUserRole(
            org_id=org.id, user_id=user.id, role_id=owner_role.id
        )
        db.add(role_link)

    # 6. If this is the first user in the system, assign platform_admin role
    stmt_user_count = select(func.count(User.id))
    user_count_res = await db.execute(stmt_user_count)
    if user_count_res.scalar() == 1:  # The user we just added is already in DB but not committed
        stmt_platform_role = select(Role).where(
            Role.code == "platform_admin", Role.org_id.is_(None)
        )
        res_platform = await db.execute(stmt_platform_role)
        platform_role = res_platform.scalar_one_or_none()
        if platform_role:
            # Platform roles don't necessarily need an org context in OrganizationUserRole table
            # but our current schema uses org_id as part of the primary key in some tables.
            # However, for platform_admin, we can link it to their first org.
            role_link_platform = OrganizationUserRole(
                org_id=org.id, user_id=user.id, role_id=platform_role.id
            )
            db.add(role_link_platform)

    await db.commit()
    await db.refresh(user)

    return {"id": user.id, "email": user.email, "org_id": org.id}


@router.post("/login/access-token", response_model=Token)
async def login_access_token(
    db: AsyncSession = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    # 1. Authenticate
    stmt = select(User).where(User.email == form_data.username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not security.verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect email or password")

    # 2. Generate JWT
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": security.create_access_token(
            user.id, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }


@router.get("/me", response_model=UserRead)
async def read_current_user(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> Any:
    """获取当前登录用户信息"""
    # 显式加载组织信息以填充 org_id
    stmt = (
        select(User)
        .options(selectinload(User.organizations))
        .where(User.id == current_user.id)
    )
    res = await db.execute(stmt)
    full_user = res.scalar_one()

    # 将第一个组织 ID 注入响应
    user_data = UserRead.model_validate(full_user)
    if full_user.organizations:
        user_data.org_id = full_user.organizations[0].org_id

    return user_data
