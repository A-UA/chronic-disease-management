from fastapi import (
    APIRouter,
    Depends,
    UploadFile,
    File,
    HTTPException,
    BackgroundTasks,
    Form,
)
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_current_org, get_db
from app.core.config import settings
from app.db.models import User, Document, KnowledgeBase, PatientProfile
from app.services.document_parser import DocumentParseError, parse_document
from app.services.rag_ingestion import process_document
from app.services.storage import get_storage_service
from app.schemas.document import DocumentRead

router = APIRouter()

MAX_UPLOAD_BYTES = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024


@router.post("/kb/{kb_id}/documents")
async def upload_document(
    kb_id: int,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    patient_id: int | None = Form(None),
    current_user: User = Depends(get_current_user),
    org_id: int = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    try:
        kb = await db.get(KnowledgeBase, kb_id)
        if kb is None:
            raise HTTPException(status_code=404, detail="Knowledge base not found")
        if kb.org_id != org_id:
            raise HTTPException(status_code=403, detail="Not enough permissions")

        if patient_id is not None:
            patient_stmt = select(PatientProfile.id).where(
                PatientProfile.id == patient_id, PatientProfile.org_id == org_id
            )
            patient_result = await db.execute(patient_stmt)
            if patient_result.scalar_one_or_none() is None:
                raise HTTPException(status_code=404, detail="Patient profile not found")

        file_bytes = await file.read()

        if len(file_bytes) > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File size exceeds the maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB",
            )

        parsed = parse_document(file_bytes, file.filename, file.content_type)

        minio_url = await get_storage_service().upload_file(
            file_bytes=file_bytes,
            filename=file.filename,
            org_id=str(org_id),
        )

        document = Document(
            kb_id=kb_id,
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

        background_tasks.add_task(
            process_document, document.id, parsed.text, org_id, parsed.pages
        )

        return {
            "id": document.id,
            "minio_url": document.minio_url,
            "status": document.status,
        }
    except DocumentParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/kb/{kb_id}/documents", response_model=list[DocumentRead])
async def list_documents(
    kb_id: int,
    skip: int = 0,
    limit: int = 50,
    patient_id: int | None = None,
    current_user: User = Depends(get_current_user),
    org_id: int = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    """查询知识库下的文档列表"""
    kb = await db.get(KnowledgeBase, kb_id)
    if kb is None or kb.org_id != org_id:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    stmt = select(Document).where(Document.kb_id == kb_id, Document.org_id == org_id)
    if patient_id is not None:
        stmt = stmt.where(Document.patient_id == patient_id)
        
    stmt = stmt.offset(skip).limit(limit).order_by(Document.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{document_id}", response_model=DocumentRead)
async def get_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    org_id: int = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    """获取指定文档详情"""
    doc = await db.get(Document, document_id)
    if doc is None or doc.org_id != org_id:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.delete("/{document_id}", response_model=dict)
async def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    org_id: int = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    """删除文档（其包含的 Chunks 关联会自动清理）"""
    doc = await db.get(Document, document_id)
    if doc is None or doc.org_id != org_id:
        raise HTTPException(status_code=404, detail="Document not found")
        
    # TODO: 异步清理 MinIO 中的文件 (doc.minio_url)
    
    stmt = delete(Document).where(Document.id == document_id)
    await db.execute(stmt)
    await db.commit()
    return {"message": "Document deleted successfully"}
