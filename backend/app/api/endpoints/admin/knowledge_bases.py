from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from uuid import UUID
from typing import List

from app.api.deps import get_db, get_current_org, check_permission
from app.db.models import KnowledgeBase, Document
from pydantic import BaseModel, ConfigDict
from datetime import datetime

router = APIRouter()


class KBAdminRead(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    created_at: datetime
    document_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class DocumentAdminRead(BaseModel):
    id: UUID
    file_name: str
    file_type: str | None = None
    file_size: int | None = None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


@router.get("/", response_model=List[KBAdminRead])
async def list_knowledge_bases(
    org_id: UUID = Depends(get_current_org),
    _org_user=Depends(check_permission("kb:manage")),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(KnowledgeBase).where(KnowledgeBase.org_id == org_id)
    result = await db.execute(stmt)
    kbs = result.scalars().all()

    kb_reads = []
    for kb in kbs:
        count_result = await db.execute(
            select(func.count(Document.id)).where(Document.kb_id == kb.id)
        )
        doc_count = count_result.scalar() or 0
        kb_reads.append(
            KBAdminRead(
                id=kb.id,
                name=kb.name,
                description=kb.description,
                created_at=kb.created_at,
                document_count=doc_count,
            )
        )
    return kb_reads


@router.get("/{kb_id}/documents", response_model=List[DocumentAdminRead])
async def list_documents(
    kb_id: UUID,
    org_id: UUID = Depends(get_current_org),
    _org_user=Depends(check_permission("doc:manage")),
    db: AsyncSession = Depends(get_db),
):
    kb = await db.get(KnowledgeBase, kb_id)
    if not kb or kb.org_id != org_id:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    stmt = (
        select(Document)
        .where(Document.kb_id == kb_id)
        .order_by(Document.created_at.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.delete("/{kb_id}")
async def delete_knowledge_base(
    kb_id: UUID,
    org_id: UUID = Depends(get_current_org),
    _org_user=Depends(check_permission("kb:manage")),
    db: AsyncSession = Depends(get_db),
):
    kb = await db.get(KnowledgeBase, kb_id)
    if not kb or kb.org_id != org_id:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    await db.delete(kb)
    await db.commit()
    return {"status": "ok"}


@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: UUID,
    org_id: UUID = Depends(get_current_org),
    _org_user=Depends(check_permission("doc:manage")),
    db: AsyncSession = Depends(get_db),
):
    doc = await db.get(Document, doc_id)
    if not doc or doc.org_id != org_id:
        raise HTTPException(status_code=404, detail="Document not found")
    await db.delete(doc)
    await db.commit()
    return {"status": "ok"}
