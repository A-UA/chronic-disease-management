from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Organization, Tenant, UsageLog
from app.routers.deps import (
    get_current_tenant_id,
    get_current_user,
    get_db,
    get_platform_viewer,
)
from app.schemas.admin import UsageSummaryItem

router = APIRouter()


@router.get("/summary", response_model=list[UsageSummaryItem])
async def get_usage_summary(
    _admin=Depends(get_platform_viewer),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(
            UsageLog.org_id,
            Organization.name.label("org_name"),
            func.sum(UsageLog.prompt_tokens + UsageLog.completion_tokens).label(
                "total_tokens"
            ),
            func.coalesce(func.sum(UsageLog.cost), 0).label("total_cost"),
        )
        .join(Organization, Organization.id == UsageLog.org_id)
        .group_by(UsageLog.org_id, Organization.name)
        .order_by(func.sum(UsageLog.prompt_tokens + UsageLog.completion_tokens).desc())
    )
    result = await db.execute(stmt)
    return [
        UsageSummaryItem(
            org_id=r.org_id,
            org_name=r.org_name,
            total_tokens=r.total_tokens or 0,
            total_cost=float(r.total_cost or 0),
        )
        for r in result.all()
    ]


@router.get("/by-organization/{org_id}")
async def get_org_usage_detail(
    org_id: int,
    _admin=Depends(get_platform_viewer),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(
            UsageLog.user_id,
            func.sum(UsageLog.prompt_tokens + UsageLog.completion_tokens).label(
                "total_tokens"
            ),
            func.count(UsageLog.id).label("request_count"),
        )
        .where(UsageLog.org_id == org_id)
        .group_by(UsageLog.user_id)
        .order_by(func.sum(UsageLog.prompt_tokens + UsageLog.completion_tokens).desc())
    )
    result = await db.execute(stmt)
    return [
        {
            "user_id": r.user_id,
            "total_tokens": r.total_tokens or 0,
            "request_count": r.request_count,
        }
        for r in result.all()
    ]


@router.get("/my-org")
async def get_my_org_usage(
    current_user=Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """[租户级] 查看当前租户的用量汇总"""
    stmt = select(
        func.coalesce(func.sum(UsageLog.prompt_tokens + UsageLog.completion_tokens), 0)
    ).where(UsageLog.tenant_id == tenant_id)
    result = await db.execute(stmt)
    total_tokens = result.scalar() or 0

    # 查询租户配额
    tenant = await db.get(Tenant, tenant_id)
    return {
        "tenant_id": tenant_id,
        "total_tokens": total_tokens,
        "quota_limit": tenant.quota_tokens_limit if tenant else 0,
        "quota_used": tenant.quota_tokens_used if tenant else 0,
    }
