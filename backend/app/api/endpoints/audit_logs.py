from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.api.deps import (
    get_db, inject_rls_context, get_effective_org_id,
    check_permission, get_platform_viewer,
)
from app.db.models import AuditLog
from app.schemas.admin import AuditLogRead

router = APIRouter()


@router.get("", response_model=List[AuditLogRead])
async def list_audit_logs(
    skip: int = 0,
    limit: int = 50,
    action: str | None = None,
    resource_type: str | None = None,
    tenant_id: int = Depends(inject_rls_context),
    effective_org_id: int | None = Depends(get_effective_org_id),
    _org_user=Depends(check_permission("audit_log:read")),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(AuditLog).where(AuditLog.tenant_id == tenant_id)
    if effective_org_id is not None:
        stmt = stmt.where(AuditLog.org_id == effective_org_id)
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
    _admin=Depends(get_platform_viewer),
    db: AsyncSession = Depends(get_db),
):
    """平台级审计日志端点（需要 platform_viewer 权限）"""
    stmt = select(AuditLog)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if org_id_filter:
        stmt = stmt.where(AuditLog.org_id == org_id_filter)
    stmt = stmt.offset(skip).limit(limit).order_by(AuditLog.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()
