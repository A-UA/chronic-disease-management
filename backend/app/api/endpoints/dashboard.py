from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, cast, Date, text

from app.api.deps import get_db, get_current_active_user, get_current_org_user
from app.db.models import Organization, User, PatientProfile, Conversation, UsageLog, Document, OrganizationUser
from app.schemas.admin import DashboardStats, TokenTrendItem

router = APIRouter()

async def get_org_tree_ids(db: AsyncSession, root_org_id: int) -> list[int]:
    """递归获取指定组织及其所有子组织的 ID 列表"""
    query = text("""
        WITH RECURSIVE org_tree AS (
            SELECT id FROM organizations WHERE id = :root_id
            UNION ALL
            SELECT o.id FROM organizations o INNER JOIN org_tree ot ON o.parent_id = ot.id
        )
        SELECT id FROM org_tree
    """)
    result = await db.execute(query, {"root_id": root_org_id})
    return [row[0] for row in result.fetchall()]

@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_active_user),
    org_user: OrganizationUser = Depends(get_current_org_user),
    db: AsyncSession = Depends(get_db),
    x_organization_id: int | None = Header(None)
):
    """
    通用 Dashboard 统计接口：
    - 如果是平台管理员且没传 X-Organization-ID -> 返回全平台数据
    - 否则返回指定租户（含子组织）的数据
    """
    # 检查是否是平台管理员 (platform_admin 角色通常 org_id 为 None)
    is_platform_admin = any(r.code == "platform_admin" for r in org_user.rbac_roles)

    target_org_ids = None
    if not (is_platform_admin and not x_organization_id):
        # 确定起始组织 ID
        base_org_id = x_organization_id or org_user.org_id
        # 递归获取整个组织的树 ID
        target_org_ids = await get_org_tree_ids(db, base_org_id)

    # 1. 基础统计
    org_stmt = select(func.count(Organization.id))
    user_stmt = select(func.count(User.id))
    patient_stmt = select(func.count(PatientProfile.id))
    conv_stmt = select(func.count(Conversation.id))
    failed_doc_stmt = select(func.count(Document.id)).where(Document.status == "failed")
    usage_stmt = select(func.coalesce(func.sum(UsageLog.prompt_tokens + UsageLog.completion_tokens), 0))

    if target_org_ids is not None:
        # 租户级：仅统计该组织树下的数据
        # 注意：User 本身关联到 organization_users，所以需要 join
        user_stmt = select(func.count(func.distinct(OrganizationUser.user_id))).where(OrganizationUser.org_id.in_(target_org_ids))
        patient_stmt = patient_stmt.where(PatientProfile.org_id.in_(target_org_ids))
        conv_stmt = conv_stmt.where(Conversation.org_id.in_(target_org_ids))
        failed_doc_stmt = failed_doc_stmt.where(Document.org_id.in_(target_org_ids))
        usage_stmt = usage_stmt.where(UsageLog.org_id.in_(target_org_ids))
        # 组织总数在租户级即为该树的节点数
        org_count = len(target_org_ids)
    else:
        # 平台级：全量统计
        org_count = (await db.execute(org_stmt)).scalar() or 0

    user_count = (await db.execute(user_stmt)).scalar() or 0
    patient_count = (await db.execute(patient_stmt)).scalar() or 0
    conv_count = (await db.execute(conv_stmt)).scalar() or 0
    failed_docs = (await db.execute(failed_doc_stmt)).scalar() or 0
    tokens = (await db.execute(usage_stmt)).scalar() or 0

    # 24 小时活跃用户（基于 UsageLog 去重统计）
    since_24h = datetime.now(timezone.utc) - timedelta(hours=24)
    active_stmt = select(func.count(func.distinct(UsageLog.user_id))).where(
        UsageLog.created_at >= since_24h,
        UsageLog.user_id.isnot(None),
    )
    if target_org_ids is not None:
        active_stmt = active_stmt.where(UsageLog.org_id.in_(target_org_ids))
    active_users = (await db.execute(active_stmt)).scalar() or 0

    # 2. Token 趋势统计
    since_7d = (datetime.now(timezone.utc) - timedelta(days=6)).date()
    trend_stmt = (
        select(
            cast(UsageLog.created_at, Date).label("date"),
            func.sum(UsageLog.prompt_tokens + UsageLog.completion_tokens).label("count")
        )
        .where(UsageLog.created_at >= since_7d)
        .group_by(cast(UsageLog.created_at, Date))
        .order_by("date")
    )
    if target_org_ids is not None:
        trend_stmt = trend_stmt.where(UsageLog.org_id.in_(target_org_ids))

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
        recent_failed_docs=failed_docs
    )
