"""健康指标业务服务"""

from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.base.exceptions import ForbiddenError, NotFoundError, ValidationError
from app.models import HealthMetric, PatientProfile
from app.repositories.health_metric_repo import HealthMetricRepository
from app.schemas.health_metric import ALLOWED_METRIC_TYPES
from app.services.patient.health_alert import check_metric_alert


class HealthMetricService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = HealthMetricRepository(db)

    async def _get_my_patient(self, user_id: int, org_id: int) -> PatientProfile:
        """获取当前用户的患者档案"""
        patient = await self.repo.find_patient_by_user_and_org(user_id, org_id)
        if not patient:
            raise NotFoundError("Patient profile")
        return patient

    async def create_metric(
        self,
        *,
        user_id: int,
        tenant_id: int,
        org_id: int,
        metric_type: str,
        value: float,
        value_secondary: float | None = None,
        unit: str,
        measured_at: datetime,
        note: str | None = None,
    ) -> dict:
        """录入健康指标（含告警检测）"""
        patient = await self._get_my_patient(user_id, org_id)

        metric = HealthMetric(
            patient_id=patient.id,
            tenant_id=tenant_id,
            org_id=org_id,
            recorded_by=user_id,
            metric_type=metric_type,
            value=value,
            value_secondary=value_secondary,
            unit=unit,
            measured_at=measured_at,
            note=note,
        )
        await self.repo.create(metric)
        await self.db.commit()

        # 告警检测
        alerts = check_metric_alert(metric_type, value, value_secondary)

        return {
            "id": metric.id,
            "patient_id": metric.patient_id,
            "metric_type": metric.metric_type,
            "value": metric.value,
            "value_secondary": metric.value_secondary,
            "unit": metric.unit,
            "measured_at": str(metric.measured_at),
            "note": metric.note,
            "alerts": [{"level": a.level, "message": a.message} for a in alerts]
            if alerts
            else [],
        }

    async def list_my_metrics(
        self,
        user_id: int,
        org_id: int,
        *,
        metric_type: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[HealthMetric]:
        """查看自己的健康指标列表"""
        patient = await self._get_my_patient(user_id, org_id)
        return await self.repo.list_by_patient(
            patient.id, metric_type=metric_type, skip=skip, limit=limit
        )

    async def get_my_trend(
        self,
        user_id: int,
        org_id: int,
        metric_type: str,
        days: int = 30,
    ) -> list[HealthMetric]:
        """按类型获取健康指标趋势"""
        patient = await self._get_my_patient(user_id, org_id)
        since = datetime.now(timezone.utc) - timedelta(days=days)
        return await self.repo.get_trend(patient.id, metric_type, since)

    async def update_metric(
        self,
        metric_id: int,
        user_id: int,
        tenant_id: int,
        data: dict,
    ) -> dict:
        """修正健康指标记录（仅限本人录入）"""
        metric = await self.repo.get_by_id(metric_id)
        if not metric or metric.tenant_id != tenant_id:
            raise NotFoundError("Metric", metric_id)
        if metric.recorded_by != user_id:
            raise ForbiddenError("Can only edit your own records")

        await self.repo.update(metric, data)
        await self.db.commit()
        return {"status": "ok", "id": metric.id}

    async def delete_metric(
        self,
        metric_id: int,
        user_id: int,
        tenant_id: int,
    ) -> None:
        """删除健康指标记录（仅限本人录入）"""
        metric = await self.repo.get_by_id(metric_id)
        if not metric or metric.tenant_id != tenant_id:
            raise NotFoundError("Metric", metric_id)
        if metric.recorded_by != user_id:
            raise ForbiddenError("Can only delete your own records")

        await self.repo.delete(metric)
        await self.db.commit()

    async def get_patient_trend(
        self,
        patient_id: int,
        metric_type: str,
        tenant_id: int,
        effective_org_id: int | None,
        days: int = 30,
    ) -> list[HealthMetric]:
        """[管理端] 查看指定患者的健康指标趋势"""
        if metric_type not in ALLOWED_METRIC_TYPES:
            raise ValidationError(f"Invalid metric_type: {metric_type}")

        patient = await self.db.get(PatientProfile, patient_id)
        if not patient or patient.tenant_id != tenant_id:
            raise NotFoundError("Patient", patient_id)
        if effective_org_id is not None and patient.org_id != effective_org_id:
            raise NotFoundError("Patient", patient_id)

        since = datetime.now(timezone.utc) - timedelta(days=days)
        return await self.repo.get_trend(patient_id, metric_type, since)
