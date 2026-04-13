"""API Key 端点 — 纯 HTTP 适配层"""

from fastapi import APIRouter, Depends

from app.models import User
from app.routers.deps import (
    ApiKeyServiceDep,
    check_permission,
    get_current_active_user,
    get_current_org_id,
    get_current_tenant_id,
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
    service: ApiKeyServiceDep,
    tenant_id: int = Depends(get_current_tenant_id),
    org_id: int = Depends(get_current_org_id),
    current_user: User = Depends(get_current_active_user),
    _org_member=Depends(check_permission("org_member:manage")),
):
    """创建 API Key（需组织管理权限）"""
    return await service.create_api_key(
        tenant_id=tenant_id, org_id=org_id, user_id=current_user.id, data=data.model_dump()
    )


@router.get("", response_model=list[ApiKeyRead])
async def list_api_keys(
    service: ApiKeyServiceDep,
    skip: int = 0,
    limit: int = 50,
    org_id: int = Depends(get_current_org_id),
    _org_member=Depends(check_permission("org_member:manage")),
):
    """列出当前组织的 API Keys"""
    return await service.list_api_keys(org_id=org_id, skip=skip, limit=limit)


@router.patch("/{api_key_id}", response_model=ApiKeyRead)
async def update_api_key(
    api_key_id: int,
    data: ApiKeyUpdate,
    service: ApiKeyServiceDep,
    org_id: int = Depends(get_current_org_id),
    _org_member=Depends(check_permission("org_member:manage")),
):
    """更新 API Key 属性/状态"""
    return await service.update_api_key(
        api_key_id=api_key_id, org_id=org_id, data=data.model_dump(exclude_unset=True)
    )


@router.post("/{api_key_id}/revoke", response_model=ApiKeyRead)
async def revoke_api_key(
    api_key_id: int,
    service: ApiKeyServiceDep,
    org_id: int = Depends(get_current_org_id),
    _org_member=Depends(check_permission("org_member:manage")),
):
    """吊销 API Key"""
    return await service.revoke_api_key(api_key_id=api_key_id, org_id=org_id)
