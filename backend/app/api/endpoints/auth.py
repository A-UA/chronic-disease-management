from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import uuid4

from app.api.deps import get_db, get_current_user, get_current_user
from app.core import security
from app.core.config import settings
from app.db.models import (
    User,
    Organization,
    OrganizationUser,
    OrganizationUserRole,
    Role,
)
from app.schemas.user import UserCreate, Token
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
