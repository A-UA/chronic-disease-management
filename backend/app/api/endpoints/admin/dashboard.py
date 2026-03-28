from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.api.deps import get_db, get_platform_viewer
from app.db.models import Organization, User, PatientProfile, Conversation, UsageLog
from app.schemas.admin import DashboardStats

router = APIRouter()


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    _admin=Depends(get_platform_viewer),
    db: AsyncSession = Depends(get_db),
):
    org_count = (await db.execute(select(func.count(Organization.id)))).scalar() or 0
    user_count = (await db.execute(select(func.count(User.id)))).scalar() or 0
    patient_count = (
        await db.execute(select(func.count(PatientProfile.id)))
    ).scalar() or 0
    conv_count = (await db.execute(select(func.count(Conversation.id)))).scalar() or 0
    tokens = (
        await db.execute(
            select(
                func.coalesce(
                    func.sum(UsageLog.prompt_tokens + UsageLog.completion_tokens), 0
                )
            )
        )
    ).scalar() or 0

    return DashboardStats(
        total_organizations=org_count,
        total_users=user_count,
        total_patients=patient_count,
        total_conversations=conv_count,
        total_tokens_used=tokens,
    )
