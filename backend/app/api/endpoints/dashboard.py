from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Header, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, cast, Date

from app.api.deps import get_db, get_current_active_user, get_platform_viewer
from app.db.models import Organization, User, PatientProfile, Conversation, UsageLog, Document
from app.schemas.admin import DashboardStats, TokenTrendItem

router = APIRouter()

@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    x_organization_id: Optional[int] = Header(None)
):
    """
    通用 Dashboard 统计接口：
    - 如果是平台管理员且没传 X-Organization-ID -> 返回全平台数据
    - 否则返回指定租户（或默认租户）的数据
    """
    is_platform_admin = current_user.role_code == "platform_admin"
    
    # 确定查询范围（Scope）
    target_org_id = None if (is_platform_admin and not x_organization_id) else (x_organization_id or current_user.org_id)

    # 1. 基础统计
    # 平台级则查全量，租户级则查 org_id
    org_stmt = select(func.count(Organization.id))
    user_stmt = select(func.count(User.id))
    patient_stmt = select(func.count(PatientProfile.id))
    conv_stmt = select(func.count(Conversation.id))
    failed_doc_stmt = select(func.count(Document.id)).where(Document.status == "failed")
    usage_stmt = select(func.coalesce(func.sum(UsageLog.prompt_tokens + UsageLog.completion_tokens), 0))

    if target_org_id:
        user_stmt = user_stmt.where(User.org_id == target_org_id)
        patient_stmt = patient_stmt.where(PatientProfile.org_id == target_org_id)
        conv_stmt = conv_stmt.where(Conversation.org_id == target_org_id)
        failed_doc_stmt = failed_doc_stmt.where(Document.org_id == target_org_id)
        usage_stmt = usage_stmt.where(UsageLog.org_id == target_org_id)

    org_count = (await db.execute(org_stmt)).scalar() or 0
    user_count = (await db.execute(user_stmt)).scalar() or 0
    patient_count = (await db.execute(patient_stmt)).scalar() or 0
    conv_count = (await db.execute(conv_stmt)).scalar() or 0
    failed_docs = (await db.execute(failed_doc_stmt)).scalar() or 0
    tokens = (await db.execute(usage_stmt)).scalar() or 0

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
    if target_org_id:
        trend_stmt = trend_stmt.where(UsageLog.org_id == target_org_id)
        
    trend_res = await db.execute(trend_stmt)
    trend_data = {row.date.isoformat(): row.count for row in trend_res.all()}
    
    full_trend = []
    for i in range(7):
        d = (since_7d + timedelta(days=i)).isoformat()
        full_trend.append(TokenTrendItem(date=d, tokens=trend_data.get(d, 0)))

    return DashboardStats(
        total_organizations=org_count if not target_org_id else 1,
        total_users=user_count,
        active_users_24h=0, # TODO: 活跃用户逻辑类似
        total_patients=patient_count,
        total_conversations=conv_count,
        total_tokens_used=tokens,
        token_usage_trend=full_trend,
        recent_failed_docs=failed_docs
    )
