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
from app.db.models import User, OrganizationUser, Organization, ApiKey
from app.services.quota import check_org_quota, check_api_key_rate_limit
import hashlib

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

async def verify_quota(
    org_id: UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db)
) -> Organization:
    return await check_org_quota(db, org_id)

async def get_api_key_context(
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db)
) -> ApiKey:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization header")
    
    token = authorization.replace("Bearer ", "")
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    
    stmt = select(ApiKey).where(ApiKey.key_hash == token_hash, ApiKey.status == 'active')
    result = await db.execute(stmt)
    api_key = result.scalar_one_or_none()
    
    if not api_key:
        raise HTTPException(status_code=401, detail="Invalid API Key")
        
    # Rate Limiting
    check_api_key_rate_limit(api_key.id, api_key.qps_limit)
    
    # Verify Quota (org level)
    await check_org_quota(db, api_key.org_id)
    
    # Key level quota if exists
    if api_key.token_quota is not None and api_key.token_used >= api_key.token_quota:
        raise HTTPException(status_code=402, detail="API Key token quota exceeded")
        
    # RLS
    await db.execute(text("SET LOCAL app.current_org_id = :org_id"), {"org_id": str(api_key.org_id)})
    
    return api_key
