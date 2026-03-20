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
from sqlalchemy.orm import selectinload
from app.db.models import User, OrganizationUser, Organization, ApiKey, Role, Permission
from app.services.quota import check_org_quota, check_api_key_rate_limit
import hashlib

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/login/access-token")

async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except (jwt.PyJWTError, ValidationError):
        raise HTTPException(status_code=401, detail="Could not validate credentials")
    
    user = await db.get(User, UUID(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Inject User ID for RLS (e.g. for cross-org family access)
    await db.execute(text("SELECT set_config('app.current_user_id', :user_id, true)"), {"user_id": str(user.id)})
    
    return user

async def get_current_org_user(
    x_organization_id: str = Header(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> OrganizationUser:
    try:
        org_uuid = UUID(x_organization_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Organization ID")

    # Verify user belongs to org and load RBAC info
    stmt = (
        select(OrganizationUser)
        .options(
            selectinload(OrganizationUser.rbac_roles).selectinload(Role.permissions)
        )
        .where(
            OrganizationUser.org_id == org_uuid,
            OrganizationUser.user_id == current_user.id
        )
    )
    result = await db.execute(stmt)
    org_user = result.scalar_one_or_none()
    
    if not org_user:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Inject RLS context
    await db.execute(text("SELECT set_config('app.current_org_id', :org_id, true)"), {"org_id": str(org_uuid)})
    
    return org_user

async def get_current_org(
    org_user: OrganizationUser = Depends(get_current_org_user)
) -> UUID:
    return org_user.org_id

def check_permission(perm_code: str):
    async def permission_dependency(
        org_user: OrganizationUser = Depends(get_current_org_user)
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
                detail=f"Missing required permission: {perm_code}"
            )
        return org_user
        
    return permission_dependency

async def require_patient_identity(
    org_user: OrganizationUser = Depends(get_current_org_user),
    db: AsyncSession = Depends(get_db)
) -> UUID:
    """
    Ensure the user is acting as a patient in this organization.
    Returns the patient_profile.id.
    """
    if org_user.user_type != "patient":
         # Maybe they are a staff but also have a patient profile? Let's check.
         from app.db.models import PatientProfile
         stmt = select(PatientProfile.id).where(
             PatientProfile.user_id == org_user.user_id,
             PatientProfile.org_id == org_user.org_id
         )
         res = await db.execute(stmt)
         patient_id = res.scalar()
         if not patient_id:
             raise HTTPException(status_code=403, detail="User is not a patient in this organization")
         return patient_id
    
    # If they are explicitly marked as patient type, find their profile
    from app.db.models import PatientProfile
    stmt = select(PatientProfile.id).where(
        PatientProfile.user_id == org_user.user_id,
        PatientProfile.org_id == org_user.org_id
    )
    res = await db.execute(stmt)
    patient_id = res.scalar()
    if not patient_id:
        raise HTTPException(status_code=404, detail="Patient profile not found")
    return patient_id

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
    await check_api_key_rate_limit(api_key.id, api_key.qps_limit)
    
    # Verify Quota (org level)
    await check_org_quota(db, api_key.org_id)
    
    # Key level quota if exists
    if api_key.token_quota is not None and api_key.token_used >= api_key.token_quota:
        raise HTTPException(status_code=402, detail="API Key token quota exceeded")
        
    # RLS
    await db.execute(text("SELECT set_config('app.current_org_id', :org_id, true)"), {"org_id": str(api_key.org_id)})
    
    return api_key
