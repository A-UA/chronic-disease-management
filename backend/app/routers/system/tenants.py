"""租户管理 CRUD 端点"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.routers.deps import check_permission, get_current_org_id, get_db
from app.models import Organization, OrganizationUser, Tenant
from app.services.audit.service import fire_audit

router = APIRouter()


# ── Schemas（内联，避免循环导入） ──

from datetime import datetime

from pydantic import BaseModel, ConfigDict


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
    skip: int = 0,
    limit: int = 50,
    search: str | None = None,
    status: str | None = None,
    _perm=Depends(check_permission("tenant:manage")),
    db: AsyncSession = Depends(get_db),
):
    """[管理员] 租户列表（分页+搜索）"""
    base = select(Tenant)
    if search:
        base = base.where(Tenant.name.ilike(f"%{search}%") | Tenant.slug.ilike(f"%{search}%"))
    if status:
        base = base.where(Tenant.status == status)

    # 总数
    count_stmt = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    # 分页数据
    stmt = base.order_by(Tenant.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    tenants = result.scalars().all()

    reads = []
    for t in tenants:
        org_count = (await db.execute(
            select(func.count()).where(Organization.tenant_id == t.id)
        )).scalar() or 0
        reads.append(TenantRead(
            id=t.id, name=t.name, slug=t.slug, status=t.status,
            plan_type=t.plan_type,
            quota_tokens_limit=t.quota_tokens_limit,
            quota_tokens_used=t.quota_tokens_used,
            max_members=t.max_members, max_patients=t.max_patients,
            contact_name=t.contact_name, contact_phone=t.contact_phone,
            contact_email=t.contact_email, org_type=t.org_type,
            address=t.address, org_count=org_count,
            created_at=t.created_at,
        ))
    return {"total": total, "items": reads}


@router.get("/{tenant_id}", response_model=TenantRead)
async def get_tenant(
    tenant_id: int,
    _perm=Depends(check_permission("tenant:manage")),
    db: AsyncSession = Depends(get_db),
):
    """[管理员] 租户详情"""
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    org_count = (await db.execute(
        select(func.count()).where(Organization.tenant_id == tenant.id)
    )).scalar() or 0
    return TenantRead(
        id=tenant.id, name=tenant.name, slug=tenant.slug, status=tenant.status,
        plan_type=tenant.plan_type,
        quota_tokens_limit=tenant.quota_tokens_limit,
        quota_tokens_used=tenant.quota_tokens_used,
        max_members=tenant.max_members, max_patients=tenant.max_patients,
        contact_name=tenant.contact_name, contact_phone=tenant.contact_phone,
        contact_email=tenant.contact_email, org_type=tenant.org_type,
        address=tenant.address, org_count=org_count,
        created_at=tenant.created_at,
    )


@router.post("", response_model=TenantRead)
async def create_tenant(
    data: TenantCreate,
    org_id: int = Depends(get_current_org_id),
    _perm: OrganizationUser = Depends(check_permission("tenant:manage")),
    db: AsyncSession = Depends(get_db),
):
    """[管理员] 创建租户（自动创建默认组织）"""
    # 唯一性检查
    stmt = select(Tenant).where(Tenant.slug == data.slug)
    if (await db.execute(stmt)).scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Slug already exists")

    tenant = Tenant(**data.model_dump())
    db.add(tenant)
    await db.flush()

    # 自动创建默认组织
    default_org = Organization(
        tenant_id=tenant.id,
        name=f"{tenant.name} - 默认部门",
        code="DEFAULT",
        status="active",
    )
    db.add(default_org)
    await db.flush()

    fire_audit(
        user_id=_perm.user_id, org_id=org_id,
        action="CREATE_TENANT", resource_type="tenant",
        resource_id=tenant.id, details=f"Created tenant: {tenant.name} (with default org)",
    )

    await db.commit()
    await db.refresh(tenant)
    return TenantRead(
        id=tenant.id, name=tenant.name, slug=tenant.slug, status=tenant.status,
        plan_type=tenant.plan_type,
        quota_tokens_limit=tenant.quota_tokens_limit,
        quota_tokens_used=tenant.quota_tokens_used,
        max_members=tenant.max_members, max_patients=tenant.max_patients,
        contact_name=tenant.contact_name, contact_phone=tenant.contact_phone,
        contact_email=tenant.contact_email, org_type=tenant.org_type,
        address=tenant.address, org_count=1, created_at=tenant.created_at,
    )


@router.put("/{tenant_id}", response_model=TenantRead)
async def update_tenant(
    tenant_id: int,
    data: TenantUpdate,
    org_id: int = Depends(get_current_org_id),
    _perm: OrganizationUser = Depends(check_permission("tenant:manage")),
    db: AsyncSession = Depends(get_db),
):
    """[管理员] 更新租户"""
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # slug 唯一性检查
    if data.slug and data.slug != tenant.slug:
        stmt = select(Tenant).where(Tenant.slug == data.slug, Tenant.id != tenant_id)
        if (await db.execute(stmt)).scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Slug already exists")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(tenant, field, value)

    fire_audit(
        user_id=_perm.user_id, org_id=org_id,
        action="UPDATE_TENANT", resource_type="tenant",
        resource_id=tenant.id, details=f"Updated tenant: {tenant.name}",
    )

    await db.commit()
    await db.refresh(tenant)
    org_count = (await db.execute(
        select(func.count()).where(Organization.tenant_id == tenant.id)
    )).scalar() or 0
    return TenantRead(
        id=tenant.id, name=tenant.name, slug=tenant.slug, status=tenant.status,
        plan_type=tenant.plan_type,
        quota_tokens_limit=tenant.quota_tokens_limit,
        quota_tokens_used=tenant.quota_tokens_used,
        max_members=tenant.max_members, max_patients=tenant.max_patients,
        contact_name=tenant.contact_name, contact_phone=tenant.contact_phone,
        contact_email=tenant.contact_email, org_type=tenant.org_type,
        address=tenant.address, org_count=org_count, created_at=tenant.created_at,
    )


@router.delete("/{tenant_id}")
async def delete_tenant(
    tenant_id: int,
    org_id: int = Depends(get_current_org_id),
    _perm: OrganizationUser = Depends(check_permission("tenant:manage")),
    db: AsyncSession = Depends(get_db),
):
    """[管理员] 删除租户（检查关联组织）"""
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    org_count = (await db.execute(
        select(func.count()).where(Organization.tenant_id == tenant.id)
    )).scalar() or 0
    if org_count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Tenant still has {org_count} organization(s). Remove them first.",
        )

    fire_audit(
        user_id=_perm.user_id, org_id=org_id,
        action="DELETE_TENANT", resource_type="tenant",
        resource_id=tenant.id, details=f"Deleted tenant: {tenant.name}",
    )

    await db.delete(tenant)
    await db.commit()
    return {"status": "ok"}
