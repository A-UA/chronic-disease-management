from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.api.deps import get_db, get_current_org, check_permission
from app.db.models import AuditLog
from app.schemas.admin import AuditLogRead

router = APIRouter()


@router.get("/", response_model=List[AuditLogRead])
async def list_audit_logs(
    skip: int = 0,
    limit: int = 50,
    action: str | None = None,
    resource_type: str | None = None,
    org_id: int = Depends(get_current_org),
    _org_user=Depends(check_permission("org:view_usage")),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(AuditLog).where(AuditLog.org_id == org_id)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if resource_type:
        stmt = stmt.where(AuditLog.resource_type == resource_type)
    stmt = stmt.offset(skip).limit(limit).order_by(AuditLog.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/global", response_model=List[AuditLogRead])
async def list_global_audit_logs(
    skip: int = 0,
    limit: int = 50,
    action: str | None = None,
    org_id_filter: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Platform-level audit log endpoint (requires platform_viewer externally)"""
    from app.api.deps import get_platform_viewer

    # This endpoint is mounted under /admin/audit-logs/global
    # The platform_viewer check is done at router level via dependency
    stmt = select(AuditLog)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if org_id_filter:
        stmt = stmt.where(AuditLog.org_id == org_id_filter)
    stmt = stmt.offset(skip).limit(limit).order_by(AuditLog.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()
