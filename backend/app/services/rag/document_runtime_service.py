"""文档运行时业务服务"""

from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.exceptions import NotFoundError
from app.models import User
from app.repositories.kb_repo import ChunkRepository, DocumentRepository, KnowledgeBaseRepository
from app.services.rag.document_service import (
    delete_document_and_enqueue_cleanup,
    upload_document_and_enqueue,
)


class DocumentRuntimeService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.kb_repo = KnowledgeBaseRepository(db)
        self.doc_repo = DocumentRepository(db)
        self.chunk_repo = ChunkRepository(db)

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
        kb = await self.kb_repo.get_by_id(kb_id)
        if not kb or kb.tenant_id != tenant_id:
            raise NotFoundError("Knowledge base", kb_id)

        docs = await self.doc_repo.list_with_chunk_count(
            kb_id=kb_id,
            tenant_id=tenant_id,
            org_id=effective_org_id,
            patient_id=patient_id,
            skip=skip,
            limit=limit,
        )

        return [
            {
                "id": doc.id, "kb_id": doc.kb_id, "org_id": doc.org_id, "uploader_id": doc.uploader_id,
                "patient_id": doc.patient_id, "file_name": doc.file_name, "file_type": doc.file_type,
                "file_size": doc.file_size, "minio_url": doc.minio_url, "status": doc.status,
                "failed_reason": doc.failed_reason, "chunk_count": doc.chunk_count,
                "created_at": doc.created_at, "updated_at": doc.updated_at,
            }
            for doc in docs
        ]

    async def _get_doc(self, document_id: int, tenant_id: int):
        doc = await self.doc_repo.get_by_id(document_id)
        if not doc or doc.tenant_id != tenant_id:
            raise NotFoundError("Document", document_id)
        return doc

    async def get_document(self, document_id: int, tenant_id: int) -> dict:
        """获取文档信息"""
        doc = await self._get_doc(document_id, tenant_id)
        # 简单抽象方法
        from app.models import Chunk
        chunk_count = await self.chunk_repo.count(filters=[Chunk.document_id == document_id, Chunk.deleted_at.is_(None)])

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
