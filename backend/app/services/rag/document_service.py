from __future__ import annotations

import logging

from fastapi import HTTPException, UploadFile
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.config import settings
from app.base.storage import get_storage_service
from app.models import Document, KnowledgeBase, PatientProfile, User
from app.plugins.parser.base import DocumentParseError
from app.services.rag.provider_service import provider_service
from app.services.rag.tasks import enqueue_delete_file_job, enqueue_process_document_job

logger = logging.getLogger(__name__)

MAX_UPLOAD_BYTES = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024


async def _read_upload_bytes(file: UploadFile) -> bytes:
    chunks = []
    total_size = 0
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total_size += len(chunk)
        if total_size > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"文件大小超过最大限制 {settings.MAX_UPLOAD_SIZE_MB}MB",
            )
        chunks.append(chunk)
    return b"".join(chunks)


async def upload_document_and_enqueue(
    *,
    kb_id: int,
    file: UploadFile,
    patient_id: int | None,
    current_user: User,
    tenant_id: int,
    org_id: int,
    db: AsyncSession,
) -> dict[str, object]:
    kb = await db.get(KnowledgeBase, kb_id)
    if kb is None:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    if kb.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    if patient_id is not None:
        patient_stmt = select(PatientProfile.id).where(
            PatientProfile.id == patient_id,
            PatientProfile.tenant_id == tenant_id,
        )
        patient_result = await db.execute(patient_stmt)
        if patient_result.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="Patient profile not found")

    file_bytes = await _read_upload_bytes(file)
    parser = provider_service.get_parser_for_filename(file.filename)

    try:
        parsed = parser.parse(file_bytes, file.filename)
    except DocumentParseError:
        raise
    except Exception as exc:
        raise DocumentParseError(str(exc)) from exc

    minio_url = await get_storage_service().upload_file(
        file_bytes=file_bytes,
        filename=file.filename,
        org_id=str(org_id),
    )

    document = Document(
        kb_id=kb_id,
        tenant_id=tenant_id,
        org_id=org_id,
        uploader_id=current_user.id,
        patient_id=patient_id,
        file_name=file.filename,
        file_type=file.content_type,
        file_size=len(file_bytes),
        minio_url=minio_url,
        status="pending",
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)

    try:
        await enqueue_process_document_job(
            document_id=document.id,
            file_content=parsed.text,
            org_id=org_id,
            pages=parsed.pages,
        )
    except Exception as exc:
        logger.exception("Failed to enqueue document processing")
        document.status = "failed"
        document.failed_reason = f"enqueue_failed: {type(exc).__name__}"
        await db.commit()
        raise HTTPException(status_code=500, detail="Document enqueue failed") from exc

    return {
        "id": document.id,
        "minio_url": document.minio_url,
        "status": document.status,
    }


async def delete_document_and_enqueue_cleanup(
    *,
    document,
    db: AsyncSession,
) -> None:
    try:
        if document.minio_url:
            await enqueue_delete_file_job(minio_url=document.minio_url)
    except Exception as exc:
        logger.exception("Failed to enqueue file deletion")
        raise HTTPException(
            status_code=500, detail="Document cleanup enqueue failed"
        ) from exc

    await db.execute(delete(Document).where(Document.id == document.id))
    await db.commit()
