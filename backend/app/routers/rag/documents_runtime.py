import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.storage import get_storage_service
from app.models import Chunk, Document, KnowledgeBase, User
from app.plugins.parser.base import DocumentParseError
from app.routers.deps import (
    get_current_tenant_id,
    get_current_user,
    get_db,
    get_effective_org_id,
    inject_rls_context,
    get_current_org_id,
)
from app.schemas.document import DocumentRead
from app.services.rag.document_service import upload_document_and_enqueue

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/kb/{kb_id}/documents")
async def upload_document(
    kb_id: int,
    file: UploadFile = File(...),
    patient_id: int | None = Form(None),
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
    org_id: int = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await upload_document_and_enqueue(
            kb_id=kb_id,
            file=file,
            patient_id=patient_id,
            current_user=current_user,
            tenant_id=tenant_id,
            org_id=org_id,
            db=db,
        )
    except DocumentParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception:
        logger.exception("文档上传处理失败")
        raise HTTPException(status_code=500, detail="文档上传处理失败，请稍后重试")


@router.get("/kb/{kb_id}/documents", response_model=list[DocumentRead])
async def list_documents(
    kb_id: int,
    skip: int = 0,
    limit: int = 50,
    patient_id: int | None = None,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(inject_rls_context),
    effective_org_id: int | None = Depends(get_effective_org_id),
    db: AsyncSession = Depends(get_db),
):
    kb = await db.get(KnowledgeBase, kb_id)
    if kb is None or kb.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    chunk_count_sq = (
        select(
            Chunk.document_id,
            func.count(Chunk.id).label("chunk_count"),
        )
        .where(Chunk.deleted_at.is_(None))
        .group_by(Chunk.document_id)
        .subquery()
    )

    stmt = (
        select(
            Document,
            func.coalesce(chunk_count_sq.c.chunk_count, 0).label("chunk_count"),
        )
        .outerjoin(chunk_count_sq, Document.id == chunk_count_sq.c.document_id)
        .where(Document.kb_id == kb_id, Document.tenant_id == tenant_id)
    )
    if effective_org_id is not None:
        stmt = stmt.where(Document.org_id == effective_org_id)
    if patient_id is not None:
        stmt = stmt.where(Document.patient_id == patient_id)

    stmt = stmt.offset(skip).limit(limit).order_by(Document.created_at.desc())
    result = await db.execute(stmt)
    rows = result.all()
    return [
        DocumentRead(
            id=doc.id,
            kb_id=doc.kb_id,
            org_id=doc.org_id,
            uploader_id=doc.uploader_id,
            patient_id=doc.patient_id,
            file_name=doc.file_name,
            file_type=doc.file_type,
            file_size=doc.file_size,
            minio_url=doc.minio_url,
            status=doc.status,
            failed_reason=doc.failed_reason,
            chunk_count=chunk_cnt,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
        )
        for doc, chunk_cnt in rows
    ]


@router.get("/{document_id}", response_model=DocumentRead)
async def get_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(inject_rls_context),
    db: AsyncSession = Depends(get_db),
):
    doc = await db.get(Document, document_id)
    if doc is None or doc.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Document not found")

    chunk_count = (
        await db.execute(
            select(func.count(Chunk.id)).where(
                Chunk.document_id == document_id,
                Chunk.deleted_at.is_(None),
            )
        )
    ).scalar() or 0

    return DocumentRead(
        id=doc.id,
        kb_id=doc.kb_id,
        org_id=doc.org_id,
        uploader_id=doc.uploader_id,
        patient_id=doc.patient_id,
        file_name=doc.file_name,
        file_type=doc.file_type,
        file_size=doc.file_size,
        minio_url=doc.minio_url,
        status=doc.status,
        failed_reason=doc.failed_reason,
        chunk_count=chunk_count,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


@router.delete("/{document_id}", response_model=dict)
async def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(inject_rls_context),
    db: AsyncSession = Depends(get_db),
):
    doc = await db.get(Document, document_id)
    if doc is None or doc.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Document not found")

    minio_url = doc.minio_url
    if minio_url:
        await get_storage_service().delete_file(minio_url)

    stmt = delete(Document).where(Document.id == document_id)
    await db.execute(stmt)
    await db.commit()
    return {"message": "Document deleted successfully"}


@router.get("/{document_id}/status")
async def get_document_status(
    document_id: int,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(inject_rls_context),
    db: AsyncSession = Depends(get_db),
):
    doc = await db.get(Document, document_id)
    if doc is None or doc.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "document_id": doc.id,
        "status": doc.status,
        "failed_reason": doc.failed_reason,
        "file_name": doc.file_name,
    }
