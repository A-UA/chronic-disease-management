"""审计模块路由 — 纯 HTTP 适配层"""

from fastapi import APIRouter, Depends

from app.routers.deps import (
    AuditQueryServiceDep,
    check_permission,
    get_effective_org_id,
    get_platform_viewer,
    inject_rls_context,
)
from app.schemas.admin import AuditLogRead

router = APIRouter()


@router.get("", response_model=list[AuditLogRead])
async def list_audit_logs(
    service: AuditQueryServiceDep,
    skip: int = 0,
    limit: int = 50,
    action: str | None = None,
    resource_type: str | None = None,
    tenant_id: int = Depends(inject_rls_context),
    effective_org_id: int | None = Depends(get_effective_org_id),
    _org_user=Depends(check_permission("audit_log:read")),
):
    """筛选当前租户的审计日志"""
    return await service.list_audit_logs(
        tenant_id=tenant_id, effective_org_id=effective_org_id,
        action=action, resource_type=resource_type, skip=skip, limit=limit
    )


@router.get("/global", response_model=list[AuditLogRead])
async def list_global_audit_logs(
    service: AuditQueryServiceDep,
    skip: int = 0,
    limit: int = 50,
    action: str | None = None,
    org_id_filter: int | None = None,
    _admin=Depends(get_platform_viewer),
):
    """平台级审计日志（需要 platform_viewer 权限）"""
    return await service.list_global_audit_logs(
        action=action, org_id_filter=org_id_filter, skip=skip, limit=limit
    )
