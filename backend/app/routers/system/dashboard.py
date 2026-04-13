"""仪表盘端点 — 纯 HTTP 适配层"""

from fastapi import APIRouter, Depends

from app.routers.deps import (
    DashboardServiceDep,
    check_permission,
    get_current_tenant_id,
    inject_rls_context,
)

router = APIRouter()


@router.get("/stats")
async def get_dashboard_stats(
    service: DashboardServiceDep,
    tenant_id: int = Depends(inject_rls_context),
    _=Depends(check_permission("org_usage:read")),
):
    """[管理员] 获取租户级仪表盘统计"""
    return await service.get_tenant_stats(tenant_id)


@router.get("/platform-stats")
async def get_platform_stats(
    service: DashboardServiceDep,
    _=Depends(check_permission("org_usage:read")),
):
    """[超管] 平台级统计"""
    return await service.get_platform_stats()


@router.get("/token-trend")
async def get_token_trend(
    service: DashboardServiceDep,
    days: int = 30,
    tenant_id: int = Depends(get_current_tenant_id),
    _=Depends(check_permission("org_usage:read")),
):
    """[管理员] Token 使用趋势"""
    return await service.get_token_trend(tenant_id, days)
