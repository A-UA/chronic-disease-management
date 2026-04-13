"""租户管理业务服务"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.base.exceptions import ConflictError, NotFoundError
from app.models import Organization, Tenant
from app.repositories.org_repo import OrganizationRepository
from app.repositories.tenant_repo import TenantRepository
from app.services.audit.service import fire_audit


class TenantService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = TenantRepository(db)
        self.org_repo = OrganizationRepository(db)

    async def _tenant_read(self, t: Tenant) -> dict:
        """构建 TenantRead dict"""
        org_count = await self.org_repo.count(filters=[Organization.tenant_id == t.id])
        return {
            "id": t.id,
            "name": t.name,
            "slug": t.slug,
            "status": t.status,
            "plan_type": t.plan_type,
            "quota_tokens_limit": t.quota_tokens_limit,
            "quota_tokens_used": t.quota_tokens_used,
            "max_members": t.max_members,
            "max_patients": t.max_patients,
            "contact_name": t.contact_name,
            "contact_phone": t.contact_phone,
            "contact_email": t.contact_email,
            "org_type": t.org_type,
            "address": t.address,
            "org_count": org_count,
            "created_at": t.created_at,
        }

    async def list_tenants(
        self, *, search: str | None = None, status: str | None = None, skip: int = 0, limit: int = 50
    ) -> dict:
        """租户列表"""
        total, tenants = await self.repo.list_with_filters(search=search, status=status, skip=skip, limit=limit)
        reads = [await self._tenant_read(t) for t in tenants]
        return {"total": total, "items": reads}

    async def get_tenant(self, tenant_id: int) -> dict:
        """租户详情"""
        tenant = await self.repo.get_by_id(tenant_id)
        if not tenant:
            raise NotFoundError("Tenant", tenant_id)
        return await self._tenant_read(tenant)

    async def create_tenant(
        self, data: dict, *, user_id: int, org_id: int
    ) -> dict:
        """创建租户（自动创建默认组织）"""
        slug = data.get("slug")
        if slug and await self.repo.check_slug_exists(slug):
            raise ConflictError("Slug already exists")

        tenant = Tenant(**data)
        await self.repo.create(tenant)

        default_org = Organization(
            tenant_id=tenant.id,
            name=f"{tenant.name} - 默认部门",
            code="DEFAULT",
            status="active",
        )
        await self.org_repo.create(default_org)

        fire_audit(
            user_id=user_id,
            org_id=org_id,
            action="CREATE_TENANT",
            resource_type="tenant",
            resource_id=tenant.id,
            details=f"Created tenant: {tenant.name} (with default org)",
        )

        await self.db.commit()
        await self.db.refresh(tenant)
        result = await self._tenant_read(tenant)
        result["org_count"] = 1  # 刚创建的默认组织
        return result

    async def update_tenant(
        self, tenant_id: int, data: dict, *, user_id: int, org_id: int
    ) -> dict:
        """更新租户"""
        tenant = await self.repo.get_by_id(tenant_id)
        if not tenant:
            raise NotFoundError("Tenant", tenant_id)

        slug = data.get("slug")
        if slug and slug != tenant.slug and await self.repo.check_slug_exists(slug, exclude_id=tenant_id):
            raise ConflictError("Slug already exists")

        await self.repo.update(tenant, data)

        fire_audit(
            user_id=user_id,
            org_id=org_id,
            action="UPDATE_TENANT",
            resource_type="tenant",
            resource_id=tenant.id,
            details=f"Updated tenant: {tenant.name}",
        )

        await self.db.commit()
        await self.db.refresh(tenant)
        return await self._tenant_read(tenant)

    async def delete_tenant(
        self, tenant_id: int, *, user_id: int, org_id: int
    ) -> None:
        """删除租户"""
        tenant = await self.repo.get_by_id(tenant_id)
        if not tenant:
            raise NotFoundError("Tenant", tenant_id)

        org_count = await self.org_repo.count(filters=[Organization.tenant_id == tenant.id])
        if org_count > 0:
            raise ConflictError(
                f"Tenant still has {org_count} organization(s). Remove them first."
            )

        fire_audit(
            user_id=user_id,
            org_id=org_id,
            action="DELETE_TENANT",
            resource_type="tenant",
            resource_id=tenant.id,
            details=f"Deleted tenant: {tenant.name}",
        )

        await self.repo.delete(tenant)
        await self.db.commit()
