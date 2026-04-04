from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import AuditLog

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
    """
    Log an action for auditing and compliance.
    In production, this could be sent to an asynchronous queue (Celery/RabbitMQ) 
    to avoid blocking the main request.
    """
    log = AuditLog(
        tenant_id=tenant_id,
        user_id=user_id,
        org_id=org_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ip_address=ip_address
    )
    db.add(log)
    # We don't await commit here to allow the caller to decide when to commit,
    # or the caller can call this within their transaction.
