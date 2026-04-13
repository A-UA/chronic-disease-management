"""用量查询业务服务"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Tenant
from app.repositories.usage_repo import UsageRepository
from app.schemas.admin import UsageSummaryItem


class UsageService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = UsageRepository(db)

    async def get_usage_summary(self) -> list[UsageSummaryItem]:
        """获取所有组织的用量汇总"""
        rows = await self.repo.get_summary_by_orgs()
        return [
            UsageSummaryItem(
                org_id=r.org_id, org_name=r.org_name,
                total_tokens=r.total_tokens or 0, total_cost=float(r.total_cost or 0),
            )
            for r in rows
        ]

    async def get_org_usage_detail(self, org_id: int) -> list[dict]:
        """获取某组织的汇总详情"""
        rows = await self.repo.get_org_usage_detail(org_id)
        return [
            {
                "user_id": r.user_id,
                "total_tokens": r.total_tokens or 0,
                "request_count": r.request_count,
            }
            for r in rows
        ]

    async def get_my_org_usage(self, tenant_id: int) -> dict:
        """获取当前租户用量"""
        total_tokens = await self.repo.get_tenant_total_tokens(tenant_id)
        tenant = await self.db.get(Tenant, tenant_id) # 也可以建 TenantRepo，此处由于只get一次，直接get是可以的，但最好也迁移
        return {
            "tenant_id": tenant_id,
            "total_tokens": total_tokens,
            "quota_limit": tenant.quota_tokens_limit if tenant else 0,
            "quota_used": tenant.quota_tokens_used if tenant else 0,
        }
