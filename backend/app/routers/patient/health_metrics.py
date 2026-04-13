"""健康指标管理端点 — 纯 HTTP 适配层"""

from typing import Any

from fastapi import APIRouter, Depends

from app.models import User
from app.routers.deps import (
    HealthMetricServiceDep,
    check_permission,
    get_current_org_id,
    get_current_tenant_id,
    get_current_user,
    get_effective_org_id,
    inject_rls_context,
)
from app.schemas.health_metric import HealthMetricCreate, HealthMetricUpdate

router = APIRouter()


# ── 个人端点 ──


@router.post("")
async def create_health_metric(
    data: HealthMetricCreate,
    service: HealthMetricServiceDep,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
    org_id: int = Depends(get_current_org_id),
) -> Any:
    """录入健康指标"""
    return await service.create_metric(
        user_id=current_user.id,
        tenant_id=tenant_id,
        org_id=org_id,
        metric_type=data.metric_type,
        value=data.value,
        value_secondary=data.value_secondary,
        unit=data.unit,
        measured_at=data.measured_at,
        note=data.note,
    )


@router.get("/me")
async def list_my_metrics(
    service: HealthMetricServiceDep,
    metric_type: str | None = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    org_id: int = Depends(get_current_org_id),
) -> Any:
    """查看自己的健康指标列表"""
    return await service.list_my_metrics(
        current_user.id, org_id, metric_type=metric_type, skip=skip, limit=limit
    )


@router.get("/me/trend")
async def get_my_trend(
    metric_type: str,
    service: HealthMetricServiceDep,
    days: int = 30,
    current_user: User = Depends(get_current_user),
    org_id: int = Depends(get_current_org_id),
) -> Any:
    """按类型获取健康指标趋势（时间序列）"""
    return await service.get_my_trend(current_user.id, org_id, metric_type, days)


@router.put("/{metric_id}")
async def update_health_metric(
    metric_id: int,
    data: HealthMetricUpdate,
    service: HealthMetricServiceDep,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(inject_rls_context),
) -> Any:
    """修正健康指标记录（仅限本人录入）"""
    return await service.update_metric(
        metric_id, current_user.id, tenant_id, data.model_dump(exclude_unset=True)
    )


@router.delete("/{metric_id}")
async def delete_health_metric(
    metric_id: int,
    service: HealthMetricServiceDep,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(inject_rls_context),
) -> Any:
    """删除健康指标记录（仅限本人录入的记录）"""
    await service.delete_metric(metric_id, current_user.id, tenant_id)
    return {"status": "ok"}


# ── 管理端接口 ──


@router.get("/patients/{patient_id}/trend")
async def get_patient_trend(
    patient_id: int,
    metric_type: str,
    service: HealthMetricServiceDep,
    days: int = 30,
    _perm=Depends(check_permission("patient:read")),
    tenant_id: int = Depends(inject_rls_context),
    effective_org_id: int | None = Depends(get_effective_org_id),
) -> Any:
    """[管理端] 查看指定患者的健康指标趋势"""
    return await service.get_patient_trend(
        patient_id, metric_type, tenant_id, effective_org_id, days
    )
