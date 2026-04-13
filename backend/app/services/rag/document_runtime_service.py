"""文档运行时业务服务"""

from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.exceptions import NotFoundError
from app.models import Chunk, Document, KnowledgeBase, User
from app.services.rag.document_service import (
    delete_document_and_enqueue_cleanup,
    upload_document_and_enqueue,
)


class DocumentRuntimeService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def upload_document(
        self, *, kb_id: int, file: UploadFile, patient_id: int | None,
        current_user: User, tenant_id: int, org_id: int
    ):
        """上传文档并投递入库任务"""
        return await upload_document_and_enqueue(
            kb_id=kb_id, file=file, patient_id=patient_id,
            current_user=current_user, tenant_id=tenant_id, org_id=org_id, db=self.db
        )

    async def list_documents(
        self, *, kb_id: int, tenant_id: int, effective_org_id: int | None,
        patient_id: int | None, skip: int = 0, limit: int = 50
    ) -> list[dict]:
        """列出知识库文档"""
        kb = await self.db.get(KnowledgeBase, kb_id)
        if not kb or kb.tenant_id != tenant_id:
            raise NotFoundError("Knowledge base", kb_id)

        chunk_count_sq = (
            select(Chunk.document_id, func.count(Chunk.id).label("chunk_count"))
            .where(Chunk.deleted_at.is_(None))
            .group_by(Chunk.document_id)
            .subquery()
        )

        stmt = (
            select(Document, func.coalesce(chunk_count_sq.c.chunk_count, 0).label("chunk_count"))
            .outerjoin(chunk_count_sq, Document.id == chunk_count_sq.c.document_id)
            .where(Document.kb_id == kb_id, Document.tenant_id == tenant_id)
        )
        if effective_org_id is not None:
            stmt = stmt.where(Document.org_id == effective_org_id)
        if patient_id is not None:
            stmt = stmt.where(Document.patient_id == patient_id)

        stmt = stmt.offset(skip).limit(limit).order_by(Document.created_at.desc())
        result = await self.db.execute(stmt)

        return [
            {
                "id": doc.id, "kb_id": doc.kb_id, "org_id": doc.org_id, "uploader_id": doc.uploader_id,
                "patient_id": doc.patient_id, "file_name": doc.file_name, "file_type": doc.file_type,
                "file_size": doc.file_size, "minio_url": doc.minio_url, "status": doc.status,
                "failed_reason": doc.failed_reason, "chunk_count": chunk_cnt,
                "created_at": doc.created_at, "updated_at": doc.updated_at,
            }
            for doc, chunk_cnt in result.all()
        ]

    async def _get_doc(self, document_id: int, tenant_id: int) -> Document:
        doc = await self.db.get(Document, document_id)
        if not doc or doc.tenant_id != tenant_id:
            raise NotFoundError("Document", document_id)
        return doc

    async def get_document(self, document_id: int, tenant_id: int) -> dict:
        """获取文档信息"""
        doc = await self._get_doc(document_id, tenant_id)
        chunk_count = (await self.db.execute(
            select(func.count(Chunk.id)).where(Chunk.document_id == document_id, Chunk.deleted_at.is_(None))
        )).scalar() or 0

        return {
            "id": doc.id, "kb_id": doc.kb_id, "org_id": doc.org_id, "uploader_id": doc.uploader_id,
            "patient_id": doc.patient_id, "file_name": doc.file_name, "file_type": doc.file_type,
            "file_size": doc.file_size, "minio_url": doc.minio_url, "status": doc.status,
            "failed_reason": doc.failed_reason, "chunk_count": chunk_count,
            "created_at": doc.created_at, "updated_at": doc.updated_at,
        }

    async def delete_document(self, document_id: int, tenant_id: int) -> dict:
        """删除文档库并异步清理文件与知识块"""
        doc = await self._get_doc(document_id, tenant_id)
        await delete_document_and_enqueue_cleanup(document=doc, db=self.db)
        return {"message": "Document deleted successfully"}

    async def get_document_status(self, document_id: int, tenant_id: int) -> dict:
        """获取文档状态"""
        doc = await self._get_doc(document_id, tenant_id)
        return {
            "document_id": doc.id, "status": doc.status,
            "failed_reason": doc.failed_reason, "file_name": doc.file_name,
        }
