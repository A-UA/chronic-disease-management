from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.api.deps import get_current_user, get_current_org, get_db
from app.db.models import User, Document
from app.services.document_parser import DocumentParseError, parse_document
from app.services.storage import storage_service
from app.services.rag import process_document

router = APIRouter()

@router.post("/kb/{kb_id}/documents")
async def upload_document(
    kb_id: UUID,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    org_id: UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db)
):
    try:
        file_bytes = await file.read()
        
        # Upload to MinIO
        minio_url = storage_service.upload_file(
            file_bytes=file_bytes,
            filename=file.filename,
            org_id=str(org_id)
        )
        
        # Save to DB
        document = Document(
            kb_id=kb_id,
            org_id=org_id,
            uploader_id=current_user.id,
            file_name=file.filename,
            file_type=file.content_type,
            file_size=len(file_bytes),
            minio_url=minio_url,
            status="pending"
        )
        db.add(document)
        await db.commit()
        await db.refresh(document)
        
        try:
            parsed = parse_document(file_bytes, file.filename, file.content_type)
        except DocumentParseError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
            
        background_tasks.add_task(process_document, document.id, parsed.text)
        
        return {"id": document.id, "minio_url": document.minio_url, "status": document.status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
