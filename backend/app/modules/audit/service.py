"""审计日志服务

提供同步（事务内）和异步（后台任务）两种写入方式。
从 services/audit.py 迁移，保持接口完全兼容。
"""
import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditLog

logger = logging.getLogger(__name__)


async def audit_action(
    db: AsyncSession,
    user_id: int,
    org_id: int | None,
    action: str,
    resource_type: str,
    resource_id: int | None = None,
    details: str | None = None,
    ip_address: str | None = None,
    tenant_id: int | None = None,
) -> None:
    """同步审计记录（在调用方事务内写入，不单独 commit）"""
    log = AuditLog(
        tenant_id=tenant_id,
        user_id=user_id,
        org_id=org_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ip_address=ip_address,
    )
    db.add(log)


async def audit_action_async(
    user_id: int,
    org_id: int | None,
    action: str,
    resource_type: str,
    resource_id: int | None = None,
    details: str | None = None,
    ip_address: str | None = None,
    tenant_id: int | None = None,
) -> None:
    """异步审计记录（后台任务，独立会话，不阻塞请求）"""
    try:
        from app.db.session import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            if tenant_id:
                from sqlalchemy import text
                await db.execute(
                    text("SELECT set_config('app.current_tenant_id', :tid, true)"),
                    {"tid": str(tenant_id)},
                )
            log = AuditLog(
                tenant_id=tenant_id,
                user_id=user_id,
                org_id=org_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                details=details,
                ip_address=ip_address,
            )
            db.add(log)
            await db.commit()
    except Exception:
        logger.exception("异步审计日志写入失败")


def fire_audit(
    user_id: int,
    org_id: int | None,
    action: str,
    resource_type: str,
    resource_id: int | None = None,
    details: str | None = None,
    ip_address: str | None = None,
    tenant_id: int | None = None,
) -> None:
    """即发即忘式审计记录（适用于不需要等待结果的场景）"""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(audit_action_async(
            user_id=user_id,
            org_id=org_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            tenant_id=tenant_id,
        ))
    except RuntimeError:
        logger.warning("无事件循环，审计日志跳过")
