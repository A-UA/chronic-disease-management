"""知识库管理端点 — 纯 HTTP 适配层"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from app.models import User
from app.routers.deps import (
    KBServiceDep,
    get_current_org_id,
    get_current_tenant_id,
    get_current_user,
    get_effective_org_id,
    inject_rls_context,
)

router = APIRouter()


class KBCreate(BaseModel):
    name: str
    description: str | None = None


class KBUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class KBRead(BaseModel):
    id: int
    name: str
    description: str | None
    org_id: int
    document_count: int = 0
    chunk_count: int = 0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


@router.post("", response_model=KBRead)
async def create_knowledge_base(
    kb_in: KBCreate,
    service: KBServiceDep,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
    org_id: int = Depends(get_current_org_id),
) -> Any:
    """创建知识库"""
    return await service.create_kb(
        tenant_id=tenant_id, org_id=org_id, created_by=current_user.id,
        name=kb_in.name, description=kb_in.description,
    )


@router.get("", response_model=list[KBRead])
async def list_knowledge_bases(
    service: KBServiceDep,
    skip: int = 0,
    limit: int = 100,
    tenant_id: int = Depends(inject_rls_context),
    effective_org_id: int | None = Depends(get_effective_org_id),
) -> Any:
    """列出知识库"""
    return await service.list_kbs(tenant_id, effective_org_id, skip, limit)


@router.put("/{kb_id}", response_model=KBRead)
async def update_knowledge_base(
    kb_id: int,
    data: KBUpdate,
    service: KBServiceDep,
    tenant_id: int = Depends(inject_rls_context),
    effective_org_id: int | None = Depends(get_effective_org_id),
) -> Any:
    """更新知识库"""
    return await service.update_kb(kb_id, tenant_id, effective_org_id, data.model_dump(exclude_unset=True))


@router.delete("/{kb_id}")
async def delete_knowledge_base(
    kb_id: int,
    service: KBServiceDep,
    tenant_id: int = Depends(inject_rls_context),
    effective_org_id: int | None = Depends(get_effective_org_id),
) -> Any:
    """删除知识库"""
    await service.delete_kb(kb_id, tenant_id, effective_org_id)
    return {"status": "ok"}


@router.get("/{kb_id}/stats")
async def get_knowledge_base_stats(
    kb_id: int,
    service: KBServiceDep,
    tenant_id: int = Depends(inject_rls_context),
    effective_org_id: int | None = Depends(get_effective_org_id),
) -> Any:
    """知识库统计"""
    return await service.get_kb_stats(kb_id, tenant_id, effective_org_id)
