"""健康指标数据访问"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import HealthMetric, PatientProfile
from app.repositories.base import BaseRepository


class HealthMetricRepository(BaseRepository[HealthMetric]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, HealthMetric)

    async def find_patient_by_user_and_org(
        self, user_id: int, org_id: int
    ) -> PatientProfile | None:
        """获取当前用户的患者档案"""
        stmt = select(PatientProfile).where(
            PatientProfile.user_id == user_id,
            PatientProfile.org_id == org_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_patient(
        self,
        patient_id: int,
        *,
        metric_type: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[HealthMetric]:
        """按患者查询指标列表"""
        filters = [HealthMetric.patient_id == patient_id]
        if metric_type:
            filters.append(HealthMetric.metric_type == metric_type)
        return await self.list(
            filters=filters,
            skip=skip,
            limit=limit,
            order_by=HealthMetric.measured_at.desc(),
        )

    async def get_trend(
        self,
        patient_id: int,
        metric_type: str,
        since: datetime,
    ) -> list[HealthMetric]:
        """按时间范围查趋势数据"""
        stmt = (
            select(HealthMetric)
            .where(
                HealthMetric.patient_id == patient_id,
                HealthMetric.metric_type == metric_type,
                HealthMetric.measured_at >= since,
            )
            .order_by(HealthMetric.measured_at.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
