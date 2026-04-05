from datetime import datetime
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import (
    get_db, get_current_user, get_current_org_id, get_effective_org_id,
    get_current_tenant_id, inject_rls_context,
)
from app.db.models import User, KnowledgeBase
from pydantic import BaseModel, ConfigDict

router = APIRouter()


class KBCreate(BaseModel):
    name: str
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
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
    org_id: int = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db),
) -> Any:
    # 逻辑已经在 get_current_org 中校验了权限和 RLS
    kb = KnowledgeBase(
        tenant_id=tenant_id,
        org_id=org_id,
        created_by=current_user.id,
        name=kb_in.name,
        description=kb_in.description,
    )
    db.add(kb)
    await db.commit()
    await db.refresh(kb)
    return KBRead(
        id=kb.id,
        name=kb.name,
        description=kb.description,
        org_id=kb.org_id,
        document_count=0,
        chunk_count=0,
        created_at=kb.created_at,
    )


@router.get("", response_model=list[KBRead])
async def list_knowledge_bases(
    skip: int = 0,
    limit: int = 100,
    tenant_id: int = Depends(inject_rls_context),
    effective_org_id: int | None = Depends(get_effective_org_id),
    db: AsyncSession = Depends(get_db),
) -> Any:
    from sqlalchemy import func
    from app.db.models import Document, Chunk

    # 子查询：每个 KB 的文档数
    doc_count_sq = (
        select(
            Document.kb_id,
            func.count(Document.id).label("document_count"),
        )
        .group_by(Document.kb_id)
        .subquery()
    )

    # 子查询：每个 KB 的切块数
    chunk_count_sq = (
        select(
            Chunk.kb_id,
            func.count(Chunk.id).label("chunk_count"),
        )
        .group_by(Chunk.kb_id)
        .subquery()
    )

    stmt = (
        select(
            KnowledgeBase,
            func.coalesce(doc_count_sq.c.document_count, 0).label("document_count"),
            func.coalesce(chunk_count_sq.c.chunk_count, 0).label("chunk_count"),
        )
        .outerjoin(doc_count_sq, KnowledgeBase.id == doc_count_sq.c.kb_id)
        .outerjoin(chunk_count_sq, KnowledgeBase.id == chunk_count_sq.c.kb_id)
        .where(KnowledgeBase.tenant_id == tenant_id)
    )
    if effective_org_id is not None:
        stmt = stmt.where(KnowledgeBase.org_id == effective_org_id)
    stmt = stmt.offset(skip).limit(limit)

    result = await db.execute(stmt)
    rows = result.all()
    return [
        KBRead(
            id=kb.id,
            name=kb.name,
            description=kb.description,
            org_id=kb.org_id,
            document_count=doc_cnt,
            chunk_count=chunk_cnt,
            created_at=kb.created_at,
        )
        for kb, doc_cnt, chunk_cnt in rows
    ]


@router.delete("/{kb_id}")
async def delete_knowledge_base(
    kb_id: int,
    tenant_id: int = Depends(inject_rls_context),
    effective_org_id: int | None = Depends(get_effective_org_id),
    db: AsyncSession = Depends(get_db),
) -> Any:
    kb = await db.get(KnowledgeBase, kb_id)
    if not kb or kb.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    if effective_org_id is not None and kb.org_id != effective_org_id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    await db.delete(kb)
    await db.commit()
    return {"status": "ok"}


class KBUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


@router.put("/{kb_id}")
async def update_knowledge_base(
    kb_id: int,
    data: KBUpdate,
    tenant_id: int = Depends(inject_rls_context),
    effective_org_id: int | None = Depends(get_effective_org_id),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """更新知识库名称和描述"""
    kb = await db.get(KnowledgeBase, kb_id)
    if not kb or kb.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    if effective_org_id is not None and kb.org_id != effective_org_id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(kb, field, value)
    await db.commit()
    await db.refresh(kb)
    return kb


@router.get("/{kb_id}/stats")
async def get_knowledge_base_stats(
    kb_id: int,
    tenant_id: int = Depends(inject_rls_context),
    effective_org_id: int | None = Depends(get_effective_org_id),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """获取知识库统计信息：文档数、chunk 数、总 token 数"""
    from sqlalchemy import func
    from app.db.models import Document, Chunk

    kb = await db.get(KnowledgeBase, kb_id)
    if not kb or kb.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    if effective_org_id is not None and kb.org_id != effective_org_id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # 文档数
    doc_count = (await db.execute(
        select(func.count(Document.id)).where(Document.kb_id == kb_id)
    )).scalar() or 0

    # chunk 数
    chunk_count = (await db.execute(
        select(func.count(Chunk.id)).where(Chunk.kb_id == kb_id)
    )).scalar() or 0

    # 总 token 数（从 chunk metadata 的 token_count 聚合）
    total_tokens = (await db.execute(
        select(func.coalesce(
            func.sum(Chunk.metadata_["token_count"].as_integer()), 0
        )).where(Chunk.kb_id == kb_id)
    )).scalar() or 0

    return {
        "kb_id": kb_id,
        "document_count": doc_count,
        "chunk_count": chunk_count,
        "total_tokens": total_tokens,
    }

