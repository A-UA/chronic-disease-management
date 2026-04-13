"""审计查询业务服务"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog


class AuditQueryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_audit_logs(
        self, tenant_id: int, effective_org_id: int | None,
        action: str | None, resource_type: str | None, skip: int, limit: int
    ) -> list[AuditLog]:
        """按租户/组织筛选审计日志"""
        stmt = select(AuditLog).where(AuditLog.tenant_id == tenant_id)
        if effective_org_id is not None:
            stmt = stmt.where(AuditLog.org_id == effective_org_id)
        if action:
            stmt = stmt.where(AuditLog.action == action)
        if resource_type:
            stmt = stmt.where(AuditLog.resource_type == resource_type)

        stmt = stmt.offset(skip).limit(limit).order_by(AuditLog.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_global_audit_logs(
        self, action: str | None, org_id_filter: int | None, skip: int, limit: int
    ) -> list[AuditLog]:
        """全平台查询审计日志"""
        stmt = select(AuditLog)
        if action:
            stmt = stmt.where(AuditLog.action == action)
        if org_id_filter:
            stmt = stmt.where(AuditLog.org_id == org_id_filter)

        stmt = stmt.offset(skip).limit(limit).order_by(AuditLog.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
