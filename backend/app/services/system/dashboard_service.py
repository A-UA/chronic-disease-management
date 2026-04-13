"""仪表盘统计服务"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Conversation,
    Document,
    KnowledgeBase,
    Organization,
    OrganizationUser,
    PatientProfile,
    Tenant,
    UsageLog,
    User,
)


class DashboardService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_tenant_stats(self, tenant_id: int) -> dict:
        """租户级仪表盘统计"""
        patient_count = (
            await self.db.execute(
                select(func.count()).where(PatientProfile.tenant_id == tenant_id)
            )
        ).scalar() or 0

        member_count = (
            await self.db.execute(
                select(func.count(func.distinct(OrganizationUser.user_id))).where(
                    OrganizationUser.tenant_id == tenant_id
                )
            )
        ).scalar() or 0

        org_count = (
            await self.db.execute(
                select(func.count()).where(Organization.tenant_id == tenant_id)
            )
        ).scalar() or 0

        kb_count = (
            await self.db.execute(
                select(func.count()).where(KnowledgeBase.tenant_id == tenant_id)
            )
        ).scalar() or 0

        doc_count = (
            await self.db.execute(
                select(func.count()).where(Document.tenant_id == tenant_id)
            )
        ).scalar() or 0

        conversation_count = (
            await self.db.execute(
                select(func.count()).where(Conversation.tenant_id == tenant_id)
            )
        ).scalar() or 0

        # Token 使用统计
        tenant = await self.db.get(Tenant, tenant_id)
        tokens_used = tenant.quota_tokens_used if tenant else 0
        tokens_limit = tenant.quota_tokens_limit if tenant else 0

        return {
            "patient_count": patient_count,
            "member_count": member_count,
            "org_count": org_count,
            "kb_count": kb_count,
            "doc_count": doc_count,
            "conversation_count": conversation_count,
            "tokens_used": tokens_used,
            "tokens_limit": tokens_limit,
        }

    async def get_platform_stats(self) -> dict:
        """平台级仪表盘统计（超管视图）"""
        tenant_count = (
            await self.db.execute(select(func.count()).select_from(Tenant))
        ).scalar() or 0

        user_count = (
            await self.db.execute(select(func.count()).select_from(User))
        ).scalar() or 0

        patient_count = (
            await self.db.execute(select(func.count()).select_from(PatientProfile))
        ).scalar() or 0

        kb_count = (
            await self.db.execute(select(func.count()).select_from(KnowledgeBase))
        ).scalar() or 0

        return {
            "tenant_count": tenant_count,
            "user_count": user_count,
            "patient_count": patient_count,
            "kb_count": kb_count,
        }

    async def get_token_trend(self, tenant_id: int, days: int = 30) -> list[dict]:
        """Token 使用趋势"""
        from datetime import datetime, timedelta, timezone

        since = datetime.now(timezone.utc) - timedelta(days=days)
        stmt = (
            select(
                func.date(UsageLog.created_at).label("date"),
                func.sum(UsageLog.tokens_used).label("tokens"),
            )
            .where(
                UsageLog.tenant_id == tenant_id,
                UsageLog.created_at >= since,
            )
            .group_by(func.date(UsageLog.created_at))
            .order_by(func.date(UsageLog.created_at))
        )
        result = await self.db.execute(stmt)
        return [{"date": str(row.date), "tokens": row.tokens or 0} for row in result.fetchall()]
