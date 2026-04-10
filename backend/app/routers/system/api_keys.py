import hashlib
import hmac
import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.config import settings
from app.models import ApiKey, User
from app.routers.deps import (
    check_permission,
    get_current_active_user,
    get_current_org_id,
    get_current_tenant_id,
    get_db,
)
from app.schemas.api_key import (
    ApiKeyCreate,
    ApiKeyCreateResponse,
    ApiKeyRead,
    ApiKeyUpdate,
)

router = APIRouter()


@router.post("", response_model=ApiKeyCreateResponse)
async def create_api_key(
    data: ApiKeyCreate,
    tenant_id: int = Depends(get_current_tenant_id),
    org_id: int = Depends(get_current_org_id),
    current_user: User = Depends(get_current_active_user),
    _org_member=Depends(check_permission("org_member:manage")),
    db: AsyncSession = Depends(get_db),
):
    """创建 API Key（需组织管理权限）"""
    raw_key = secrets.token_urlsafe(32)
    key_prefix = raw_key[:8]
    key_hash = hmac.new(
        settings.API_KEY_SALT.encode(), raw_key.encode(), hashlib.sha256
    ).hexdigest()

    qps_limit = data.qps_limit if data.qps_limit is not None else 10

    api_key = ApiKey(
        tenant_id=tenant_id,
        org_id=org_id,
        created_by=current_user.id,
        name=data.name,
        key_prefix=key_prefix,
        key_hash=key_hash,
        qps_limit=qps_limit,
        token_quota=data.token_quota,
        expires_at=data.expires_at,
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)

    response_dict = {
        "id": api_key.id,
        "org_id": api_key.org_id,
        "created_by": api_key.created_by,
        "name": api_key.name,
        "key_prefix": api_key.key_prefix,
        "qps_limit": api_key.qps_limit,
        "token_quota": api_key.token_quota,
        "token_used": api_key.token_used,
        "status": api_key.status,
        "expires_at": api_key.expires_at,
        "created_at": api_key.created_at,
        "updated_at": api_key.updated_at,
        "raw_key": raw_key,
    }
    return response_dict


@router.get("", response_model=list[ApiKeyRead])
async def list_api_keys(
    skip: int = 0,
    limit: int = 50,
    org_id: int = Depends(get_current_org_id),
    _org_member=Depends(check_permission("org_member:manage")),
    db: AsyncSession = Depends(get_db),
):
    """列出当前组织的 API Keys"""
    stmt = (
        select(ApiKey)
        .where(ApiKey.org_id == org_id)
        .offset(skip)
        .limit(limit)
        .order_by(ApiKey.created_at.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.patch("/{api_key_id}", response_model=ApiKeyRead)
async def update_api_key(
    api_key_id: int,
    data: ApiKeyUpdate,
    org_id: int = Depends(get_current_org_id),
    _org_member=Depends(check_permission("org_member:manage")),
    db: AsyncSession = Depends(get_db),
):
    """更新 API Key 属性/状态"""
    api_key = await db.get(ApiKey, api_key_id)
    if not api_key or api_key.org_id != org_id:
        raise HTTPException(status_code=404, detail="API Key not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(api_key, key, value)

    await db.commit()
    await db.refresh(api_key)
    return api_key


@router.post("/{api_key_id}/revoke", response_model=ApiKeyRead)
async def revoke_api_key(
    api_key_id: int,
    org_id: int = Depends(get_current_org_id),
    _org_member=Depends(check_permission("org_member:manage")),
    db: AsyncSession = Depends(get_db),
):
    """吊销 API Key"""
    api_key = await db.get(ApiKey, api_key_id)
    if not api_key or api_key.org_id != org_id:
        raise HTTPException(status_code=404, detail="API Key not found")

    api_key.status = "revoked"
    await db.commit()
    await db.refresh(api_key)
    return api_key
