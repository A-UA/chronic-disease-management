"""审计日志查询业务服务"""

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.audit_repo import AuditRepository


class AuditQueryService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AuditRepository(db)

    async def query_tenant_logs(
        self,
        tenant_id: int,
        org_id: int | None = None,
        user_id: int | None = None,
        action: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> dict:
        """租户级审计日志查询"""
        total, logs = await self.repo.list_audit_logs(
            tenant_id=tenant_id,
            org_id=org_id,
            user_id=user_id,
            action=action,
            start_time=start_time,
            end_time=end_time,
            skip=skip,
            limit=limit,
        )
        return {"total": total, "items": logs}

    async def query_platform_logs(
        self,
        tenant_id: int | None = None,
        user_id: int | None = None,
        action: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> dict:
        """全平台审计日志查询 (Owner 专用)"""
        total, logs = await self.repo.list_audit_logs(
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            start_time=start_time,
            end_time=end_time,
            skip=skip,
            limit=limit,
        )
        return {"total": total, "items": logs}
