"""Dashboard 统计端点

- 普通用户：租户级统计（admin/owner）或部门级统计（staff/manager）
- 平台管理员：全平台统计
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import Date, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Conversation,
    Document,
    Organization,
    OrganizationUser,
    PatientProfile,
    UsageLog,
    User,
)
from app.routers.deps import (
    get_current_active_user,
    get_current_roles,
    get_db,
    get_effective_org_id,
    get_platform_viewer,
    inject_rls_context,
)
from app.schemas.admin import DashboardStats, TokenTrendItem

router = APIRouter()


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_active_user),
    tenant_id: int = Depends(inject_rls_context),
    effective_org_id: int | None = Depends(get_effective_org_id),
    roles: list[str] = Depends(get_current_roles),
    db: AsyncSession = Depends(get_db),
):
    """
    Dashboard 统计接口：
    - admin/owner: 全租户统计
    - staff/manager: 本部门统计
    """
    # 1. 基础统计
    org_stmt = select(func.count(Organization.id)).where(
        Organization.tenant_id == tenant_id
    )
    patient_stmt = select(func.count(PatientProfile.id)).where(
        PatientProfile.tenant_id == tenant_id
    )
    conv_stmt = select(func.count(Conversation.id)).where(
        Conversation.tenant_id == tenant_id
    )
    failed_doc_stmt = select(func.count(Document.id)).where(
        Document.tenant_id == tenant_id, Document.status == "failed"
    )
    usage_stmt = select(
        func.coalesce(func.sum(UsageLog.prompt_tokens + UsageLog.completion_tokens), 0)
    ).where(UsageLog.tenant_id == tenant_id)
    user_stmt = select(func.count(func.distinct(OrganizationUser.user_id))).where(
        OrganizationUser.tenant_id == tenant_id
    )

    # 部门级过滤（staff/manager）
    if effective_org_id is not None:
        patient_stmt = patient_stmt.where(PatientProfile.org_id == effective_org_id)
        conv_stmt = conv_stmt.where(Conversation.org_id == effective_org_id)
        failed_doc_stmt = failed_doc_stmt.where(Document.org_id == effective_org_id)
        usage_stmt = usage_stmt.where(UsageLog.org_id == effective_org_id)
        user_stmt = user_stmt.where(OrganizationUser.org_id == effective_org_id)

    org_count = (await db.execute(org_stmt)).scalar() or 0
    user_count = (await db.execute(user_stmt)).scalar() or 0
    patient_count = (await db.execute(patient_stmt)).scalar() or 0
    conv_count = (await db.execute(conv_stmt)).scalar() or 0
    failed_docs = (await db.execute(failed_doc_stmt)).scalar() or 0
    tokens = (await db.execute(usage_stmt)).scalar() or 0

    # 24 小时活跃用户
    since_24h = datetime.utcnow() - timedelta(hours=24)
    active_stmt = select(func.count(func.distinct(UsageLog.user_id))).where(
        UsageLog.tenant_id == tenant_id,
        UsageLog.created_at >= since_24h,
        UsageLog.user_id.isnot(None),
    )
    if effective_org_id is not None:
        active_stmt = active_stmt.where(UsageLog.org_id == effective_org_id)
    active_users = (await db.execute(active_stmt)).scalar() or 0

    # 2. Token 趋势统计（最近 7 天）
    since_7d = (datetime.utcnow() - timedelta(days=6)).date()
    trend_stmt = (
        select(
            cast(UsageLog.created_at, Date).label("date"),
            func.sum(UsageLog.prompt_tokens + UsageLog.completion_tokens).label(
                "count"
            ),
        )
        .where(
            UsageLog.tenant_id == tenant_id,
            UsageLog.created_at >= since_7d,
        )
        .group_by(cast(UsageLog.created_at, Date))
        .order_by("date")
    )
    if effective_org_id is not None:
        trend_stmt = trend_stmt.where(UsageLog.org_id == effective_org_id)

    trend_res = await db.execute(trend_stmt)
    trend_data = {row.date.isoformat(): row.count for row in trend_res.all()}

    full_trend = []
    for i in range(7):
        d = (since_7d + timedelta(days=i)).isoformat()
        full_trend.append(TokenTrendItem(date=d, tokens=trend_data.get(d, 0)))

    return DashboardStats(
        total_organizations=org_count,
        total_users=user_count,
        active_users_24h=active_users,
        total_patients=patient_count,
        total_conversations=conv_count,
        total_tokens_used=tokens,
        token_usage_trend=full_trend,
        recent_failed_docs=failed_docs,
    )


@router.get("/platform-stats", response_model=DashboardStats)
async def get_platform_stats(
    _admin: User = Depends(get_platform_viewer),
    db: AsyncSession = Depends(get_db),
):
    """[平台管理员] 全平台统计（不限租户）"""
    org_count = (await db.execute(select(func.count(Organization.id)))).scalar() or 0
    user_count = (await db.execute(select(func.count(User.id)))).scalar() or 0
    patient_count = (
        await db.execute(select(func.count(PatientProfile.id)))
    ).scalar() or 0
    conv_count = (await db.execute(select(func.count(Conversation.id)))).scalar() or 0
    failed_docs = (
        await db.execute(
            select(func.count(Document.id)).where(Document.status == "failed")
        )
    ).scalar() or 0
    tokens = (
        await db.execute(
            select(
                func.coalesce(
                    func.sum(UsageLog.prompt_tokens + UsageLog.completion_tokens), 0
                )
            )
        )
    ).scalar() or 0

    since_24h = datetime.utcnow() - timedelta(hours=24)
    active_users = (
        await db.execute(
            select(func.count(func.distinct(UsageLog.user_id))).where(
                UsageLog.created_at >= since_24h, UsageLog.user_id.isnot(None)
            )
        )
    ).scalar() or 0

    since_7d = (datetime.utcnow() - timedelta(days=6)).date()
    trend_stmt = (
        select(
            cast(UsageLog.created_at, Date).label("date"),
            func.sum(UsageLog.prompt_tokens + UsageLog.completion_tokens).label(
                "count"
            ),
        )
        .where(UsageLog.created_at >= since_7d)
        .group_by(cast(UsageLog.created_at, Date))
        .order_by("date")
    )
    trend_res = await db.execute(trend_stmt)
    trend_data = {row.date.isoformat(): row.count for row in trend_res.all()}

    full_trend = []
    for i in range(7):
        d = (since_7d + timedelta(days=i)).isoformat()
        full_trend.append(TokenTrendItem(date=d, tokens=trend_data.get(d, 0)))

    return DashboardStats(
        total_organizations=org_count,
        total_users=user_count,
        active_users_24h=active_users,
        total_patients=patient_count,
        total_conversations=conv_count,
        total_tokens_used=tokens,
        token_usage_trend=full_trend,
        recent_failed_docs=failed_docs,
    )
