"""租户管理端点 — 纯 HTTP 适配层"""

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from app.models import OrganizationUser
from app.routers.deps import (
    TenantServiceDep,
    check_permission,
    get_current_org_id,
)

router = APIRouter()


# ── Schemas ──


class TenantCreate(BaseModel):
    name: str
    slug: str
    plan_type: str = "free"
    status: str = "active"
    quota_tokens_limit: int = 1_000_000
    max_members: int | None = None
    max_patients: int | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    org_type: str | None = None
    address: str | None = None


class TenantUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None
    plan_type: str | None = None
    status: str | None = None
    quota_tokens_limit: int | None = None
    max_members: int | None = None
    max_patients: int | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    org_type: str | None = None
    address: str | None = None


class TenantRead(BaseModel):
    id: int
    name: str
    slug: str
    status: str
    plan_type: str
    quota_tokens_limit: int
    quota_tokens_used: int
    max_members: int | None = None
    max_patients: int | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    org_type: str | None = None
    address: str | None = None
    org_count: int = 0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── 端点 ──


@router.get("")
async def list_tenants(
    service: TenantServiceDep,
    skip: int = 0,
    limit: int = 50,
    search: str | None = None,
    status: str | None = None,
    _perm=Depends(check_permission("tenant:manage")),
):
    """[管理员] 租户列表"""
    return await service.list_tenants(search=search, status=status, skip=skip, limit=limit)


@router.get("/{tenant_id}", response_model=TenantRead)
async def get_tenant(
    tenant_id: int,
    service: TenantServiceDep,
    _perm=Depends(check_permission("tenant:manage")),
):
    """[管理员] 租户详情"""
    return await service.get_tenant(tenant_id)


@router.post("", response_model=TenantRead)
async def create_tenant(
    data: TenantCreate,
    service: TenantServiceDep,
    org_id: int = Depends(get_current_org_id),
    _perm: OrganizationUser = Depends(check_permission("tenant:manage")),
):
    """[管理员] 创建租户"""
    return await service.create_tenant(
        data.model_dump(), user_id=_perm.user_id, org_id=org_id
    )


@router.put("/{tenant_id}", response_model=TenantRead)
async def update_tenant(
    tenant_id: int,
    data: TenantUpdate,
    service: TenantServiceDep,
    org_id: int = Depends(get_current_org_id),
    _perm: OrganizationUser = Depends(check_permission("tenant:manage")),
):
    """[管理员] 更新租户"""
    return await service.update_tenant(
        tenant_id, data.model_dump(exclude_unset=True), user_id=_perm.user_id, org_id=org_id
    )


@router.delete("/{tenant_id}")
async def delete_tenant(
    tenant_id: int,
    service: TenantServiceDep,
    org_id: int = Depends(get_current_org_id),
    _perm: OrganizationUser = Depends(check_permission("tenant:manage")),
):
    """[管理员] 删除租户"""
    await service.delete_tenant(tenant_id, user_id=_perm.user_id, org_id=org_id)
    return {"status": "ok"}
