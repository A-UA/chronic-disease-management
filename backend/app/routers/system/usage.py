"""用量查询端点 — 纯 HTTP 适配层"""

from fastapi import APIRouter, Depends

from app.routers.deps import (
    UsageServiceDep,
    get_current_tenant_id,
    get_current_user,
    get_platform_viewer,
)
from app.schemas.admin import UsageSummaryItem

router = APIRouter()


@router.get("/summary", response_model=list[UsageSummaryItem])
async def get_usage_summary(
    service: UsageServiceDep,
    _admin=Depends(get_platform_viewer),
):
    """获取全平台组织用量汇总"""
    return await service.get_usage_summary()


@router.get("/by-organization/{org_id}")
async def get_org_usage_detail(
    org_id: int,
    service: UsageServiceDep,
    _admin=Depends(get_platform_viewer),
):
    """获取指定组织的用量详情"""
    return await service.get_org_usage_detail(org_id)


@router.get("/my-org")
async def get_my_org_usage(
    service: UsageServiceDep,
    _user=Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """[租户级] 查看当前租户的用量汇总"""
    return await service.get_my_org_usage(tenant_id)
