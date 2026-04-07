"""健康指标管理端点：录入/查询/趋势/删除"""
from datetime import datetime
from typing import Any, List, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_user, get_current_org_id, get_effective_org_id,
    get_current_tenant_id, inject_rls_context, get_db, check_permission,
)
from app.db.models import User, PatientProfile, HealthMetric

router = APIRouter()

ALLOWED_METRIC_TYPES = {"blood_pressure", "blood_sugar", "weight", "heart_rate", "bmi", "spo2"}


# ── Schemas ──

class HealthMetricCreate(BaseModel):
    metric_type: Literal["blood_pressure", "blood_sugar", "weight", "heart_rate", "bmi", "spo2"]
    value: float
    value_secondary: float | None = None
    unit: str
    measured_at: datetime
    note: str | None = None


class HealthMetricRead(BaseModel):
    id: int
    patient_id: int
    metric_type: str
    value: float
    value_secondary: float | None
    unit: str
    measured_at: datetime
    note: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── 辅助函数 ──

async def _get_my_patient(db: AsyncSession, user_id: int, org_id: int) -> PatientProfile:
    """获取当前用户的患者档案"""
    stmt = select(PatientProfile).where(
        PatientProfile.user_id == user_id,
        PatientProfile.org_id == org_id,
    )
    result = await db.execute(stmt)
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient profile not found")
    return patient


# ── 个人端点（使用 get_current_org_id） ──

@router.post("")
async def create_health_metric(
    data: HealthMetricCreate,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
    org_id: int = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """录入健康指标"""
    patient = await _get_my_patient(db, current_user.id, org_id)

    metric = HealthMetric(
        patient_id=patient.id,
        tenant_id=tenant_id,
        org_id=org_id,
        recorded_by=current_user.id,
        metric_type=data.metric_type,
        value=data.value,
        value_secondary=data.value_secondary,
        unit=data.unit,
        measured_at=data.measured_at,
        note=data.note,
    )
    db.add(metric)
    await db.commit()
    await db.refresh(metric)

    # 告警检测
    from app.services.health_alert import check_metric_alert
    alerts = check_metric_alert(data.metric_type, data.value, data.value_secondary)

    return {
        "id": metric.id,
        "patient_id": metric.patient_id,
        "metric_type": metric.metric_type,
        "value": metric.value,
        "value_secondary": metric.value_secondary,
        "unit": metric.unit,
        "measured_at": str(metric.measured_at),
        "note": metric.note,
        "alerts": [
            {"level": a.level, "message": a.message}
            for a in alerts
        ] if alerts else [],
    }


@router.get("/me")
async def list_my_metrics(
    metric_type: str | None = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    org_id: int = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """查看自己的健康指标列表"""
    patient = await _get_my_patient(db, current_user.id, org_id)

    stmt = (
        select(HealthMetric)
        .where(HealthMetric.patient_id == patient.id)
        .order_by(HealthMetric.measured_at.desc())
        .offset(skip)
        .limit(limit)
    )
    if metric_type:
        stmt = stmt.where(HealthMetric.metric_type == metric_type)

    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/me/trend")
async def get_my_trend(
    metric_type: str,
    days: int = 30,
    current_user: User = Depends(get_current_user),
    org_id: int = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """按类型获取健康指标趋势（时间序列）"""
    from datetime import timedelta, timezone

    patient = await _get_my_patient(db, current_user.id, org_id)
    since = datetime.now(timezone.utc) - timedelta(days=days)

    stmt = (
        select(HealthMetric)
        .where(
            HealthMetric.patient_id == patient.id,
            HealthMetric.metric_type == metric_type,
            HealthMetric.measured_at >= since,
        )
        .order_by(HealthMetric.measured_at.asc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.delete("/{metric_id}")
async def delete_health_metric(
    metric_id: int,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(inject_rls_context),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """删除健康指标记录（仅限本人录入的记录）"""
    metric = await db.get(HealthMetric, metric_id)
    if not metric or metric.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Metric not found")
    if metric.recorded_by != current_user.id:
        raise HTTPException(status_code=403, detail="Can only delete your own records")

    await db.delete(metric)
    await db.commit()
    return {"status": "ok"}


# ── 更新健康指标 ──

class HealthMetricUpdate(BaseModel):
    value: float | None = None
    value_secondary: float | None = None
    unit: str | None = None
    note: str | None = None


@router.put("/{metric_id}")
async def update_health_metric(
    metric_id: int,
    data: HealthMetricUpdate,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(inject_rls_context),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """修正健康指标记录（仅限本人录入）"""
    metric = await db.get(HealthMetric, metric_id)
    if not metric or metric.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Metric not found")
    if metric.recorded_by != current_user.id:
        raise HTTPException(status_code=403, detail="Can only edit your own records")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(metric, field, value)
    await db.commit()
    return {"status": "ok", "id": metric.id}


# ── 管理端接口 ──

@router.get("/patients/{patient_id}/trend")
async def get_patient_trend(
    patient_id: int,
    metric_type: str,
    days: int = 30,
    _perm=Depends(check_permission("patient:read")),
    tenant_id: int = Depends(inject_rls_context),
    effective_org_id: int | None = Depends(get_effective_org_id),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """[管理端] 查看指定患者的健康指标趋势"""
    from datetime import timedelta, timezone

    if metric_type not in ALLOWED_METRIC_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid metric_type: {metric_type}")

    patient = await db.get(PatientProfile, patient_id)
    if not patient or patient.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Patient not found")
    if effective_org_id is not None and patient.org_id != effective_org_id:
        raise HTTPException(status_code=404, detail="Patient not found")

    since = datetime.now(timezone.utc) - timedelta(days=days)
    stmt = (
        select(HealthMetric)
        .where(
            HealthMetric.patient_id == patient_id,
            HealthMetric.metric_type == metric_type,
            HealthMetric.measured_at >= since,
        )
        .order_by(HealthMetric.measured_at.asc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()
