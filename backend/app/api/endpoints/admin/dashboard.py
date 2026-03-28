from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, cast, Date

from app.api.deps import get_db, get_platform_viewer
from app.db.models import Organization, User, PatientProfile, Conversation, UsageLog, Document
from app.schemas.admin import DashboardStats, TokenTrendItem

router = APIRouter()


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    _admin=Depends(get_platform_viewer),
    db: AsyncSession = Depends(get_db),
):
    # 1. Basic Counts
    org_count = (await db.execute(select(func.count(Organization.id)))).scalar() or 0
    user_count = (await db.execute(select(func.count(User.id)))).scalar() or 0
    patient_count = (
        await db.execute(select(func.count(PatientProfile.id)))
    ).scalar() or 0
    conv_count = (await db.execute(select(func.count(Conversation.id)))).scalar() or 0
    
    # 2. 24h Active Users (based on usage logs or conversations)
    # 数据库通常使用 naive datetime，确保比较时类型一致
    since_24h = datetime.utcnow() - timedelta(hours=24)
    active_users = (await db.execute(
        select(func.count(func.distinct(UsageLog.user_id)))
        .where(UsageLog.created_at >= since_24h)
    )).scalar() or 0

    # 3. Total Tokens
    tokens = (
        await db.execute(
            select(
                func.coalesce(
                    func.sum(UsageLog.prompt_tokens + UsageLog.completion_tokens), 0
                )
            )
        )
    ).scalar() or 0

    # 4. Token Usage Trend (Last 7 Days)
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
    trend_res = await db.execute(trend_stmt)
    trend_data = {row.date.isoformat(): row.count for row in trend_res.all()}
    
    # Fill gaps in trend
    full_trend = []
    for i in range(7):
        d = (since_7d + timedelta(days=i)).isoformat()
        full_trend.append(TokenTrendItem(date=d, tokens=trend_data.get(d, 0)))

    # 5. Failed Documents
    failed_docs = (await db.execute(
        select(func.count(Document.id)).where(Document.status == "failed")
    )).scalar() or 0

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
