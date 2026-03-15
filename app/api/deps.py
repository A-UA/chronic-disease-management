from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
import jwt
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from uuid import UUID

from app.core.config import settings
from app.core.security import ALGORITHM
from app.db.session import get_db
from app.db.models import User, OrganizationUser

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/login/access-token")

async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except (jwt.PyJWTError, ValidationError):
        raise HTTPException(status_code=401, detail="Could not validate credentials")
    
    user = await db.get(User, UUID(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

async def get_current_org(
    x_organization_id: str = Header(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> UUID:
    try:
        org_uuid = UUID(x_organization_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Organization ID")

    # Verify user belongs to org
    stmt = select(OrganizationUser).where(
        OrganizationUser.org_id == org_uuid,
        OrganizationUser.user_id == current_user.id
    )
    result = await db.execute(stmt)
    org_user = result.scalar_one_or_none()
    
    if not org_user:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Inject RLS context into session
    await db.execute(text("SET LOCAL app.current_org_id = :org_id"), {"org_id": str(org_uuid)})
    
    return org_uuid
