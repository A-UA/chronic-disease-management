"""工作台与统计仪表盘业务服务"""

from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.dashboard_repo import DashboardRepository


class DashboardService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = DashboardRepository(db)

    async def get_platform_dashboard(self) -> dict:
        """超级管理员：获取平台全局大盘统计数据"""
        stats = await self.repo.get_system_stats()
        return {
            "tenant_count": stats["total_tenants"],
            "org_count": stats["total_orgs"],
            "user_count": stats["total_users"],
            "patient_count": stats["total_patients"],
            "kb_count": 0,  # TODO
            "total_tokens": 0,  # TODO
            "token_trend": [],
        }

    async def get_tenant_dashboard(self, tenant_id: int, org_id: int | None = None) -> dict:
        """普通租户：获取本租户大盘统计数据"""
        # 注意：这里暂未精细到按部门 (org_id) 过滤，全租户共享
        stats = await self.repo.get_tenant_stats(tenant_id)
        
        # 简单模拟获取近 7 天趋势
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=7)
        trend = await self.repo.get_token_trend(tenant_id, start_date, end_date)

        return {
            "tenant_count": 0,
            "org_count": stats["total_orgs"],
            "user_count": stats["total_users"],
            "patient_count": stats["total_patients"],
            "kb_count": 0,
            "total_tokens": sum([t["tokens"] for t in trend]),
            "token_trend": trend,
        }
