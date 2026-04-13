from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Organization, PatientProfile, Tenant, User


class DashboardRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_system_stats(self) -> dict:
        tenant_count = (await self.db.execute(select(func.count(Tenant.id)))).scalar() or 0
        org_count = (await self.db.execute(select(func.count(Organization.id)))).scalar() or 0
        user_count = (await self.db.execute(select(func.count(User.id)))).scalar() or 0
        patient_count = (await self.db.execute(select(func.count(PatientProfile.id)))).scalar() or 0

        return {
            "total_tenants": tenant_count,
            "total_orgs": org_count,
            "total_users": user_count,
            "total_patients": patient_count,
        }

    async def get_tenant_stats(self, tenant_id: int) -> dict:
        org_count = (
            await self.db.execute(
                select(func.count(Organization.id)).where(Organization.tenant_id == tenant_id)
            )
        ).scalar() or 0
        from app.models import OrganizationUser
        user_count = (
            await self.db.execute(
                select(func.count(func.distinct(OrganizationUser.user_id))).where(
                    OrganizationUser.tenant_id == tenant_id
                )
            )
        ).scalar() or 0
        patient_count = (
            await self.db.execute(
                select(func.count(PatientProfile.id)).where(PatientProfile.tenant_id == tenant_id)
            )
        ).scalar() or 0

        return {
            "total_orgs": org_count,
            "total_users": user_count,
            "total_patients": patient_count,
        }

    async def get_token_trend(self, tenant_id: int, start_date, end_date) -> list[dict]:
        from app.models import UsageLog
        # 简化趋势统计
        stmt = (
            select(
                func.date(UsageLog.created_at).label("date"),
                func.sum(UsageLog.prompt_tokens + UsageLog.completion_tokens).label("total"),
            )
            .where(
                UsageLog.tenant_id == tenant_id,
                UsageLog.created_at >= start_date,
                UsageLog.created_at <= end_date,
            )
            .group_by(func.date(UsageLog.created_at))
            .order_by(func.date(UsageLog.created_at))
        )
        result = await self.db.execute(stmt)
        return [{"date": str(r.date), "tokens": r.total} for r in result.all()]
